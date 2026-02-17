from fastapi import FastAPI, HTTPException, Depends, UploadFile, File
from sqlalchemy.orm import Session
from minio import Minio
from minio.error import S3Error
import models
import schemas
import database
import uuid
import os
from datetime import datetime
from typing import List

app = FastAPI(title="Images Service", version="1.0.0")

# Configuration MinIO pour s'intégrer avec l'infra existante
MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "localhost:9000")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "minioadmin")
MINIO_BUCKET_NAME = os.getenv("MINIO_BUCKET_NAME", "pixtral-images")

# Initialiser MinIO client
minio_client = Minio(
    MINIO_ENDPOINT,
    access_key=MINIO_ACCESS_KEY,
    secret_key=MINIO_SECRET_KEY,
    secure=False  # False pour développement local
)

# Créer les tables
models.Base.metadata.create_all(bind=database.engine)

# Dépendance pour obtenir la session de la base de données
def get_db():
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Initialiser le bucket MinIO
@app.on_event("startup")
async def startup_event():
    try:
        if not minio_client.bucket_exists(MINIO_BUCKET_NAME):
            minio_client.make_bucket(MINIO_BUCKET_NAME)
            print(f"Bucket '{MINIO_BUCKET_NAME}' créé avec succès")
    except S3Error as e:
        print(f"Erreur MinIO: {e}")

@app.get("/health")
async def health_check():
    """Endpoint de santé pour Docker healthcheck"""
    return {"status": "healthy", "service": "images-service"}

@app.post("/api/images/upload")
async def upload_image(
    file: UploadFile = File(...),
    case_id: int = None,
    db: Session = Depends(get_db)
):
    """Uploader une image vers MinIO et sauvegarder les métadonnées"""
    try:
        # Vérifier le type de fichier
        if not file.content_type.startswith('image/'):
            raise HTTPException(status_code=400, detail="Le fichier doit être une image")
        
        # Générer un nom de fichier unique
        file_extension = file.filename.split('.')[-1]
        unique_filename = f"{uuid.uuid4()}.{file_extension}"
        object_name = f"cases/{case_id}/{unique_filename}" if case_id else f"general/{unique_filename}"
        
        # Upload vers MinIO
        try:
            file_content = await file.read()
            file.seek(0)  # Remettre le curseur au début
            
            result = minio_client.put_object(
                MINIO_BUCKET_NAME,
                object_name,
                file,
                length=len(file_content),
                content_type=file.content_type
            )
            
            # URL de l'image
            image_url = f"http://{MINIO_ENDPOINT}/{MINIO_BUCKET_NAME}/{object_name}"
            
        except S3Error as e:
            raise HTTPException(status_code=500, detail=f"Erreur upload MinIO: {str(e)}")
        
        # Sauvegarder les métadonnées dans la base de données
        db_image = models.Image(
            filename=unique_filename,
            original_filename=file.filename,
            object_name=object_name,
            content_type=file.content_type,
            size=len(file_content),
            case_id=case_id,
            url=image_url,
            uploaded_at=datetime.utcnow()
        )
        
        db.add(db_image)
        db.commit()
        db.refresh(db_image)
        
        return {
            "id": db_image.id,
            "filename": unique_filename,
            "original_filename": file.filename,
            "url": image_url,
            "size": len(file_content),
            "uploaded_at": db_image.uploaded_at
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur upload: {str(e)}")

@app.get("/api/images/", response_model=List[schemas.Image])
async def get_images(skip: int = 0, limit: int = 100, case_id: int = None, db: Session = Depends(get_db)):
    """Récupérer la liste des images"""
    query = db.query(models.Image)
    if case_id:
        query = query.filter(models.Image.case_id == case_id)
    images = query.offset(skip).limit(limit).all()
    return images

@app.get("/api/images/{image_id}", response_model=schemas.Image)
async def get_image(image_id: int, db: Session = Depends(get_db)):
    """Récupérer une image spécifique"""
    image = db.query(models.Image).filter(models.Image.id == image_id).first()
    if not image:
        raise HTTPException(status_code=404, detail="Image non trouvée")
    return image

@app.delete("/api/images/{image_id}")
async def delete_image(image_id: int, db: Session = Depends(get_db)):
    """Supprimer une image de MinIO et de la base de données"""
    image = db.query(models.Image).filter(models.Image.id == image_id).first()
    if not image:
        raise HTTPException(status_code=404, detail="Image non trouvée")
    
    try:
        # Supprimer de MinIO
        minio_client.remove_object(MINIO_BUCKET_NAME, image.object_name)
        
        # Supprimer de la base de données
        db.delete(image)
        db.commit()
        
        return {"message": "Image supprimée avec succès"}
        
    except S3Error as e:
        raise HTTPException(status_code=500, detail=f"Erreur suppression MinIO: {str(e)}")
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Erreur suppression: {str(e)}")

@app.get("/api/images/{image_id}/url")
async def get_image_url(image_id: int, db: Session = Depends(get_db)):
    """Générer une URL signée pour accéder à l'image"""
    image = db.query(models.Image).filter(models.Image.id == image_id).first()
    if not image:
        raise HTTPException(status_code=404, detail="Image non trouvée")
    
    try:
        # URL signée valide pendant 1 heure
        url = minio_client.presigned_get_object(
            MINIO_BUCKET_NAME,
            image.object_name,
            expires=3600
        )
        return {"url": url}
    except S3Error as e:
        raise HTTPException(status_code=500, detail=f"Erreur génération URL: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8004)
