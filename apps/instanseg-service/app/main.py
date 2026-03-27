from io import BytesIO
from typing import Optional

import numpy as np
from PIL import Image
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from skimage import measure
from urllib.parse import urlparse, urlunparse

import math
import xml.etree.ElementTree as ET
import requests
import os

app = FastAPI(title="InstantSeg Service")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

MODEL: Optional[object] = None
MODEL_LOAD_ERROR: Optional[str] = None


def load_model():
    global MODEL, MODEL_LOAD_ERROR
    if MODEL is not None:
        return MODEL
    if MODEL_LOAD_ERROR is not None:
        raise RuntimeError(MODEL_LOAD_ERROR)

    try:
        from instanseg import InstanSeg
        MODEL = InstanSeg("brightfield_nuclei", verbosity=1)
        print("✅ InstantSeg model loaded")
        return MODEL
    except Exception as e:
        MODEL_LOAD_ERROR = f"{type(e).__name__}: {e}"
        print(f"❌ InstantSeg load failed: {MODEL_LOAD_ERROR}")
        raise


@app.on_event("startup")
async def startup_event():
    try:
        load_model()
    except Exception:
        pass

def mask_to_polygons(label_mask: np.ndarray, offset_x: float = 0, offset_y: float = 0):
    polygons = []

    instance_ids = np.unique(label_mask)
    instance_ids = instance_ids[instance_ids > 0]

    for instance_id in instance_ids:
        binary = (label_mask == instance_id).astype(np.uint8)
        contours = measure.find_contours(binary, 0.5)

        if not contours:
            continue

        # On prend le plus grand contour
        contour = max(contours, key=lambda c: c.shape[0])

        # contour => (row, col), donc y,x
        points = []
        for row, col in contour[::4]:  # sous-échantillonnage pour alléger
            points.append({
                "x": float(col + offset_x),
                "y": float(row + offset_y),
            })

        if len(points) >= 3:
            polygons.append({
                "type": "polygon",
                "points": points,
                "label": f"InstantSeg #{int(instance_id)}",
                "confidence": None,
            })

    return polygons

def _strip_dzi_suffix(source_url: str) -> str:
    if source_url.endswith(".dzi"):
        return source_url[:-4]
    if source_url.endswith("/dzi"):
        return source_url[:-4]
    return source_url

def fetch_dzi_metadata(source_url: str, headers: Optional[dict] = None):
    resolved_url = resolve_internal_source_url(source_url)
    print(f"📡 DZI metadata URL: {resolved_url}")
    res = requests.get(resolved_url, headers=headers or {}, timeout=60)
    res.raise_for_status()

    root = ET.fromstring(res.text)
    size_el = None
    tile_size = None
    overlap = 0
    fmt = "jpeg"

    # support namespace or non-namespace XML
    if root.tag.endswith("Image"):
        tile_size = int(root.attrib.get("TileSize", 254))
        overlap = int(root.attrib.get("Overlap", 1))
        fmt = root.attrib.get("Format", "jpeg")

        for child in root:
            if child.tag.endswith("Size"):
                size_el = child
                break

    if size_el is None:
        raise ValueError("Impossible de lire les métadonnées DZI")

    width = int(size_el.attrib["Width"])
    height = int(size_el.attrib["Height"])
    max_level = math.ceil(math.log2(max(width, height)))

    return {
        "width": width,
        "height": height,
        "tile_size": tile_size,
        "overlap": overlap,
        "format": fmt,
        "max_level": max_level,
    }

def build_tile_url(source_url: str, level: int, col: int, row: int, fmt: str):
    resolved = resolve_internal_source_url(source_url)
    base = _strip_dzi_suffix(resolved)
    return f"{base}_files/{level}/{col}_{row}.{fmt}"

def extract_patch_from_dzi(
    source_url: str,
    x: int,
    y: int,
    w: int,
    h: int,
    headers: Optional[dict] = None,
) -> Image.Image:
    meta = fetch_dzi_metadata(source_url, headers=headers)

    width = meta["width"]
    height = meta["height"]
    tile_size = meta["tile_size"]
    overlap = meta["overlap"]
    fmt = meta["format"]
    level = meta["max_level"]

    x = max(0, min(x, width - 1))
    y = max(0, min(y, height - 1))
    w = max(1, min(w, width - x))
    h = max(1, min(h, height - y))

    patch = Image.new("RGB", (w, h))

    col_start = x // tile_size
    row_start = y // tile_size
    col_end = (x + w - 1) // tile_size
    row_end = (y + h - 1) // tile_size

    for row in range(row_start, row_end + 1):
        for col in range(col_start, col_end + 1):
            tile_url = build_tile_url(source_url, level, col, row, fmt)
            tile_res = requests.get(tile_url, headers=headers or {}, timeout=60)
            tile_res.raise_for_status()

            tile = Image.open(BytesIO(tile_res.content)).convert("RGB")

            nominal_x = col * tile_size
            nominal_y = row * tile_size

            left_extra = overlap if col > 0 else 0
            top_extra = overlap if row > 0 else 0

            tile_x = nominal_x - left_extra
            tile_y = nominal_y - top_extra

            inter_left = max(x, tile_x)
            inter_top = max(y, tile_y)
            inter_right = min(x + w, tile_x + tile.width)
            inter_bottom = min(y + h, tile_y + tile.height)

            if inter_right <= inter_left or inter_bottom <= inter_top:
                continue

            crop_left = inter_left - tile_x
            crop_top = inter_top - tile_y
            crop_right = inter_right - tile_x
            crop_bottom = inter_bottom - tile_y

            cropped = tile.crop((crop_left, crop_top, crop_right, crop_bottom))

            paste_x = inter_left - x
            paste_y = inter_top - y
            patch.paste(cropped, (paste_x, paste_y))

    return patch

def resolve_internal_source_url(source_url: str) -> str:
    parsed = urlparse(source_url)

    internal_host = os.getenv("IMAGES_INTERNAL_HOST", "images-service")
    internal_port = os.getenv("IMAGES_INTERNAL_PORT", "8004")

    hostname = parsed.hostname or ""
    if hostname in {"localhost", "127.0.0.1"}:
        new_netloc = internal_host
        if internal_port:
            new_netloc = f"{internal_host}:{internal_port}"

        parsed = parsed._replace(netloc=new_netloc)

    return urlunparse(parsed)

@app.post("/api/instanseg/segment")
async def segment_region(
    image: UploadFile = File(...),
    offset_x: float = Form(...),
    offset_y: float = Form(...),
):
    try:
        model = load_model()

        content = await image.read()
        pil = Image.open(BytesIO(content)).convert("RGB")
        arr = np.array(pil)

        labeled_output, _ = model.eval_small_image(arr, pixel_size=None)

        if labeled_output is None:
            return {"annotations": []}

        if hasattr(labeled_output, "cpu"):
            labeled_output = labeled_output.cpu().numpy()

        labeled_output = np.asarray(labeled_output)

        while labeled_output.ndim > 2:
            labeled_output = labeled_output[0]

        polygons = mask_to_polygons(
            labeled_output,
            offset_x=offset_x,
            offset_y=offset_y,
        )

        return {"annotations": polygons}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"{type(e).__name__}: {e}")
    

@app.post("/api/instanseg/segment-from-dzi")
async def segment_region_from_dzi(
    source_url: str = Form(...),
    x: int = Form(...),
    y: int = Form(...),
    w: int = Form(...),
    h: int = Form(...),
    authorization: Optional[str] = Header(default=None),
):
    try:
        model = load_model()

        upstream_headers = {}
        if authorization:
            upstream_headers["Authorization"] = authorization

        patch = extract_patch_from_dzi(
            source_url=source_url,
            x=x,
            y=y,
            w=w,
            h=h,
            headers=upstream_headers,
        )

        arr = np.array(patch)
        labeled_output, _ = model.eval_small_image(arr, pixel_size=None)

        if labeled_output is None:
            return {"annotations": []}

        if hasattr(labeled_output, "cpu"):
            labeled_output = labeled_output.cpu().numpy()

        labeled_output = np.asarray(labeled_output)

        while labeled_output.ndim > 2:
            labeled_output = labeled_output[0]

        polygons = mask_to_polygons(
            labeled_output,
            offset_x=float(x),
            offset_y=float(y),
        )

        return {"annotations": polygons}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"{type(e).__name__}: {e}")