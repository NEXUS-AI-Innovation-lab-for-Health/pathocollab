from fastapi import APIRouter, Query
from app.services.minio_service import MinioService

router = APIRouter(prefix="/debug/wsi-dzi", tags=["Debug WSI (DZI)"])

@router.get("")
def list_wsi_dzi(patient_id: str = Query(...)):
    minio = MinioService()
    base = f"patients/{patient_id}/dzi/"

    prefixes = minio.list_prefixes(base)  # -> patients/<id>/dzi/<wsi_id>/
    wsis = []

    for p in prefixes:
        wsi_id = p.replace(base, "").strip("/")

        dzi_obj = f"{p}slide.dzi"
        if not minio.object_exists(dzi_obj):
            # fallback: chercher n'importe quel .dzi sous le prefix (au cas où)
            objs = minio.list_objects(p)
            dzi_obj = next((o["object_name"] for o in objs if o["object_name"].lower().endswith(".dzi")), None)
            if not dzi_obj:
                continue

        wsis.append({
            "wsi_id": wsi_id,
            "dzi_object": dzi_obj,
            "filename": dzi_obj.split("/")[-1],  # typiquement "slide.dzi"
        })

    return {"wsis": wsis}