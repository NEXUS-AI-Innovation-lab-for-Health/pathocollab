from io import BytesIO
from typing import List, Dict, Any

import numpy as np
from PIL import Image
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from instanseg import InstanSeg
from skimage import measure

app = FastAPI(title="InstantSeg Service")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Chargé une seule fois au démarrage
MODEL = InstanSeg("brightfield_nuclei", verbosity=1)

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
        content = await image.read()
        pil = Image.open(BytesIO(content)).convert("RGB")
        arr = np.array(pil)

        # InstanSeg peut travailler sur tableau numpy
        # pixel_size=None ici pour un POC, à affiner ensuite si tu veux de la calibration
        labeled_output, _ = MODEL.eval_small_image(arr, pixel_size=None)

        if labeled_output is None:
            return {"annotations": []}

        if hasattr(labeled_output, "cpu"):
            labeled_output = labeled_output.cpu().numpy()

        labeled_output = np.asarray(labeled_output)

        # Si sortie avec dimensions supplémentaires
        while labeled_output.ndim > 2:
            labeled_output = labeled_output[0]

        polygons = mask_to_polygons(
            labeled_output,
            offset_x=offset_x,
            offset_y=offset_y,
        )

        return {"annotations": polygons}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))