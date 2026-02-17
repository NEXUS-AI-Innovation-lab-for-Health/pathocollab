from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.annotation import Annotation, AnnotationCreate, AnnotationDB
from typing import List
import json


router = APIRouter(prefix="/annotations", tags=["Annotations"])

def get_db_override():
    raise RuntimeError("get_db not injected")

def get_current_user_override():
    raise RuntimeError("current_user not injected")

def router_api():
    return router

@router.post("/", response_model=Annotation, status_code=201)
async def create_annotation(annotation_data: AnnotationCreate, db: AsyncSession = Depends(get_db_override), current_user = Depends(get_current_user_override)):
    db_annotation = AnnotationDB(
        image_id=annotation_data.image_id,
        case_id=annotation_data.case_id,
        user_id=current_user.id,              
        type=annotation_data.type,
        label=annotation_data.label,
        confidence=annotation_data.confidence,
        notes=annotation_data.notes,
        coordinates=json.dumps(annotation_data.coordinates),
    )

    db.add(db_annotation)
    await db.commit()
    await db.refresh(db_annotation)

    coords = getattr(db_annotation, "coordinates", None)
    if isinstance(coords, str):
        try:
            db_annotation.coordinates = json.loads(coords)
        except Exception:
            # Option: raise 400 plutôt qu'un 500
            raise HTTPException(status_code=400, detail="Invalid coordinates JSON")    
        
    annotation_dict = Annotation.model_validate(db_annotation).model_dump()

    annotation_dict["coordinates"] = json.loads(db_annotation.coordinates)
    return Annotation(**annotation_dict)


@router.put("/{annotation_id}", response_model=Annotation)
async def update_annotation(annotation_id: str, annotation_data: AnnotationCreate, db: AsyncSession = Depends(get_db_override), current_user = Depends(get_current_user_override)):
    result = await db.execute(select(AnnotationDB).where(AnnotationDB.id == annotation_id))
    ann = result.scalar_one_or_none()
    if not ann:
        raise HTTPException(status_code=404, detail="Annotation not found")

    if ann.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to update this annotation")

    ann.image_id = annotation_data.image_id
    ann.case_id = annotation_data.case_id
    ann.type = annotation_data.type
    ann.label = annotation_data.label
    ann.confidence = annotation_data.confidence
    ann.notes = annotation_data.notes
    ann.coordinates = json.dumps(annotation_data.coordinates)

    await db.commit()
    await db.refresh(ann)

    out = Annotation.model_validate(ann).model_dump()
    out["coordinates"] = json.loads(ann.coordinates)
    return Annotation(**out)


@router.delete("/{annotation_id}", status_code=204)
async def delete_annotation(annotation_id: str, db: AsyncSession = Depends(get_db_override), current_user = Depends(get_current_user_override)):
    result = await db.execute(select(AnnotationDB).where(AnnotationDB.id == annotation_id))
    ann = result.scalar_one_or_none()
    if not ann:
        raise HTTPException(status_code=404, detail="Annotation not found")

    if ann.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to delete this annotation")

    await db.delete(ann)
    await db.commit()
    return


@router.get("/image/{image_id}", response_model=List[Annotation])
async def get_image_annotations(image_id: str, db: AsyncSession = Depends(get_db_override)):
    """Récupérer toutes les annotations d'une image"""
    result = await db.execute(select(AnnotationDB).where(AnnotationDB.image_id == image_id))
    annotations = result.scalars().all()

    out = []
    for ann in annotations:
        ann_dict = Annotation.model_validate(ann).model_dump()
        ann_dict["coordinates"] = json.loads(ann.coordinates)
        out.append(Annotation(**ann_dict))
    return out


@router.get("/case/{case_id}", response_model=List[Annotation])
async def get_case_annotations(case_id: str, db: AsyncSession = Depends(get_db_override)):
    """Récupérer toutes les annotations d'un cas"""
    result = await db.execute(select(AnnotationDB).where(AnnotationDB.case_id == case_id))
    annotations = result.scalars().all()

    out = []
    for ann in annotations:
        ann_dict = Annotation.model_validate(ann).model_dump()
        ann_dict["coordinates"] = json.loads(ann.coordinates)
        out.append(Annotation(**ann_dict))
    return out
