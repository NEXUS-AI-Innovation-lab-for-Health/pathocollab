from io import BytesIO
from typing import Optional

import numpy as np
from PIL import Image
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from skimage import measure

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