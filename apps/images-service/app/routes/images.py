from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.image import Image, ImageDB, ImageUploadResponse
from app.services.minio_service import MinioService
from typing import List
import uuid


router = APIRouter(prefix="/images", tags=["Images"])
minio_service = MinioService()

def get_db_override():
    raise RuntimeError("get_db not injected")

def router_api():
    return router

@router.post("/upload", response_model=ImageUploadResponse, status_code=201)
async def upload_image(
    patient_id: str,
    case_id: str,
    uploaded_by: str,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db_override),
):
    """Uploader une image (PNG/JPG pour tests) dans MinIO + metadata DB"""
    try:
        image_id = str(uuid.uuid4())
        minio_path = f"patients/{patient_id}/cases/{case_id}/{image_id}_{file.filename}"

        file_content = await file.read()
        file_size = len(file_content)

        # Upload MinIO (sync OK)
        minio_service.upload_file(
            file_content,
            minio_path,
            file.content_type or "application/octet-stream",
        )

        # DB (async)
        db_image = ImageDB(
            id=image_id,
            case_id=case_id,
            filename=file.filename,
            minio_path=minio_path,
            mime_type=file.content_type or "application/octet-stream",
            file_size=file_size,
            uploaded_by=uploaded_by,
        )

        db.add(db_image)
        await db.commit()
        await db.refresh(db_image)

        url = minio_service.get_presigned_url(minio_path)

        return ImageUploadResponse(
            image_id=image_id,
            filename=file.filename,
            url=url,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


@router.get("/case/{case_id}", response_model=List[Image])
async def get_case_images(case_id: str, db: AsyncSession = Depends(get_db_override)):
    """Récupérer toutes les images d'un cas"""
    result = await db.execute(select(ImageDB).where(ImageDB.case_id == case_id))
    images = result.scalars().all()
    return [Image.model_validate(img) for img in images]


@router.get("/{image_id}/url")
async def get_image_url(image_id: str, db: AsyncSession = Depends(get_db_override)):
    """Générer une URL présignée pour accéder à l'image"""
    result = await db.execute(select(ImageDB).where(ImageDB.id == image_id))
    image = result.scalar_one_or_none()
    if not image:
        raise HTTPException(status_code=404, detail="Image not found")

    url = minio_service.get_presigned_url(image.minio_path)
    return {"image_id": image_id, "url": url, "filename": image.filename}


@router.get("/{image_id}/raw")
async def get_image_raw(image_id: str, db: AsyncSession = Depends(get_db_override)):
    """Récupérer l'image brute depuis MinIO (pour OpenSeadragon type:image)"""
    result = await db.execute(select(ImageDB).where(ImageDB.id == image_id))
    image = result.scalar_one_or_none()
    if not image:
        raise HTTPException(status_code=404, detail="Image not found")

    # Ici, on suppose que minio_service.get_object renvoie un objet streamable (response MinIO)
    obj = minio_service.get_object(image.minio_path)
    if obj is None:
        raise HTTPException(status_code=500, detail="Failed to retrieve image from storage")

    def iterfile():
        try:
            for chunk in obj.stream(32 * 1024):
                yield chunk
        finally:
            obj.close()
            obj.release_conn()

    return StreamingResponse(
        iterfile(),
        media_type=image.mime_type or "application/octet-stream",
        headers={"Content-Disposition": f'inline; filename="{image.filename}"'},
    )
