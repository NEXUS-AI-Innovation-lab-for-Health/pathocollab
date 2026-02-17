# app/routes/debug_browser.py
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import Response
import mimetypes

from app.services.minio_service import MinioService

router = APIRouter(prefix="/debug", tags=["Debug"])
minio = MinioService()

@router.get("/cases")
def list_cases():
    # On part du principe que vos uploads vont dans cases/<case_id>/...
    prefixes = minio.list_prefixes("cases/")
    # retourne juste les ids "propres"
    case_ids = [p.replace("cases/", "").strip("/") for p in prefixes]
    return {"cases": case_ids}

@router.get("/cases/{case_id}/images")
def list_case_images(case_id: str):
    prefix = f"cases/{case_id}/"
    objects = minio.list_objects(prefix)
    # Filtrer aux extensions image simples
    images = []
    for o in objects:
        name = o["object_name"].lower()
        if name.endswith((".png", ".jpg", ".jpeg", ".webp")):
            images.append(o)
    return {"case_id": case_id, "images": images}

@router.get("/raw")
def get_raw(object_name: str = Query(...)):
    data = minio.get_object_bytes(object_name)
    if not data:
        raise HTTPException(status_code=404, detail="Object not found")

    # Guess mime type from filename
    mime, _ = mimetypes.guess_type(object_name)
    return Response(content=data, media_type=mime or "application/octet-stream")
