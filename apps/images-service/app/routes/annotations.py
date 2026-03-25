from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.annotation import Annotation, AnnotationCreate, AnnotationDB, AnnotationType
from typing import List
import json
from datetime import datetime, timezone


router = APIRouter(prefix="/annotations", tags=["Annotations"])


def get_db_override():
    raise RuntimeError("get_db not injected")


def get_current_user_override():
    raise RuntimeError("get_current_user not injected")


def router_api():
    return router


def _json_loads_safe(value, fallback):
    if value is None:
        return fallback
    if isinstance(value, (dict, list)):
        return value
    if isinstance(value, str):
        try:
            return json.loads(value)
        except Exception:
            return fallback
    return fallback


def _serialize_annotation(db_annotation: AnnotationDB) -> Annotation:
    stroke_width = None
    try:
        stroke_width = float(db_annotation.stroke_width) if db_annotation.stroke_width is not None else None
    except Exception:
        stroke_width = None

    return Annotation(
        id=db_annotation.id,
        image_id=db_annotation.image_id,
        case_id=db_annotation.case_id,
        user_id=db_annotation.user_id,
        owner_name=db_annotation.owner_name,
        type=db_annotation.type,
        coordinates=_json_loads_safe(db_annotation.coordinates, {}),
        label=db_annotation.label,
        severity=db_annotation.severity,
        category=db_annotation.category,
        description=db_annotation.description,
        recommendation=db_annotation.recommendation,
        tags=_json_loads_safe(db_annotation.tags, []),
        stroke_color=db_annotation.stroke_color,
        fill_color=db_annotation.fill_color,
        stroke_width=stroke_width,
        confidence=db_annotation.confidence,
        notes=db_annotation.notes,
        created_at=db_annotation.created_at,
        updated_at=db_annotation.updated_at,
    )


def _extract_current_user(current_user):
    user_id = (
        getattr(current_user, "id", None)
        or getattr(current_user, "email", None)
        or getattr(current_user, "sub", None)
    )
    owner_name = (
        getattr(current_user, "full_name", None)
        or getattr(current_user, "name", None)
        or user_id
    )

    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid current user")

    return str(user_id), str(owner_name) if owner_name else None


async def _get_annotation_or_404(db: AsyncSession, annotation_id: str) -> AnnotationDB:
    result = await db.execute(
        select(AnnotationDB).where(AnnotationDB.id == annotation_id)
    )
    annotation = result.scalar_one_or_none()

    if not annotation:
        raise HTTPException(status_code=404, detail="Annotation not found")

    return annotation


def _check_annotation_owner(annotation: AnnotationDB, current_user):
    user_id, _ = _extract_current_user(current_user)

    if str(annotation.user_id) != str(user_id):
        raise HTTPException(
            status_code=403,
            detail="You are not allowed to modify this annotation",
        )


@router.post("/", response_model=Annotation, status_code=status.HTTP_201_CREATED)
async def create_annotation(
    annotation_data: AnnotationCreate,
    db: AsyncSession = Depends(get_db_override),
    current_user=Depends(get_current_user_override),
):
    user_id, owner_name = _extract_current_user(current_user)

    db_annotation = AnnotationDB(
        image_id=annotation_data.image_id,
        case_id=annotation_data.case_id,
        user_id=user_id,
        owner_name=owner_name,
        type=AnnotationType.MANUAL.value,
        label=annotation_data.label,
        severity=annotation_data.severity,
        category=annotation_data.category,
        description=annotation_data.description,
        recommendation=annotation_data.recommendation,
        tags=json.dumps(annotation_data.tags or []),
        stroke_color=annotation_data.stroke_color,
        fill_color=annotation_data.fill_color,
        stroke_width=str(annotation_data.stroke_width) if annotation_data.stroke_width is not None else None,
        confidence=annotation_data.confidence,
        notes=annotation_data.notes,
        coordinates=json.dumps(annotation_data.coordinates),
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    db.add(db_annotation)
    await db.commit()
    await db.refresh(db_annotation)

    return _serialize_annotation(db_annotation)


@router.get("/image/{image_id}", response_model=List[Annotation])
async def get_image_annotations(
    image_id: str,
    db: AsyncSession = Depends(get_db_override),
):
    result = await db.execute(
        select(AnnotationDB)
        .where(AnnotationDB.image_id == image_id)
        .order_by(AnnotationDB.created_at.desc())
    )
    annotations = result.scalars().all()
    return [_serialize_annotation(ann) for ann in annotations]


@router.get("/{annotation_id}", response_model=Annotation)
async def get_annotation(
    annotation_id: str,
    db: AsyncSession = Depends(get_db_override),
):
    annotation = await _get_annotation_or_404(db, annotation_id)
    return _serialize_annotation(annotation)


@router.put("/{annotation_id}", response_model=Annotation)
async def update_annotation(
    annotation_id: str,
    annotation_data: AnnotationCreate,
    db: AsyncSession = Depends(get_db_override),
    current_user=Depends(get_current_user_override),
):
    db_annotation = await _get_annotation_or_404(db, annotation_id)
    _check_annotation_owner(db_annotation, current_user)

    db_annotation.image_id = annotation_data.image_id
    db_annotation.case_id = annotation_data.case_id
    db_annotation.type = AnnotationType.MANUAL.value
    db_annotation.label = annotation_data.label
    db_annotation.severity = annotation_data.severity
    db_annotation.category = annotation_data.category
    db_annotation.description = annotation_data.description
    db_annotation.recommendation = annotation_data.recommendation
    db_annotation.tags = json.dumps(annotation_data.tags or [])
    db_annotation.stroke_color = annotation_data.stroke_color
    db_annotation.fill_color = annotation_data.fill_color
    db_annotation.stroke_width = (
        str(annotation_data.stroke_width)
        if annotation_data.stroke_width is not None
        else None
    )
    db_annotation.confidence = annotation_data.confidence
    db_annotation.notes = annotation_data.notes
    db_annotation.coordinates = json.dumps(annotation_data.coordinates)
    db_annotation.updated_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(db_annotation)

    return _serialize_annotation(db_annotation)


@router.delete("/{annotation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_annotation(
    annotation_id: str,
    db: AsyncSession = Depends(get_db_override),
    current_user=Depends(get_current_user_override),
):
    db_annotation = await _get_annotation_or_404(db, annotation_id)
    _check_annotation_owner(db_annotation, current_user)

    await db.delete(db_annotation)
    await db.commit()