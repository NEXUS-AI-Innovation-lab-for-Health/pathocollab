from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
import json

from app.models.case import Case, CaseCreate, CaseDB, CaseStatus
from app.utils.database import get_db

router = APIRouter(prefix="/cases", tags=["Cases"])


def get_db_override():
    raise RuntimeError("get_db not injected")


def get_current_user_override():
    raise RuntimeError("current_user not injected")


def router_api():
    return router


def _to_case_response(db_case: CaseDB) -> Case:
    """Convertit un CaseDB SQLAlchemy -> Case (Pydantic) en décodant assigned_specialists."""
    return Case(
        id=db_case.id,
        patient_id=db_case.patient_id,
        title=db_case.title,
        description=db_case.description,
        status=db_case.status,
        created_by=db_case.created_by,
        assigned_specialists=json.loads(db_case.assigned_specialists) if db_case.assigned_specialists else [],
        created_at=db_case.created_at,
        completed_at=db_case.completed_at,
    )


@router.post("/create", response_model=Case, status_code=status.HTTP_201_CREATED)
async def create_case(case_data: CaseCreate, db: AsyncSession = Depends(get_db)):
    """Créer un nouveau cas de biopsie"""
    payload = case_data.model_dump()
    assigned = payload.pop("assigned_specialists", [])

    db_case = CaseDB(
        **payload,
        assigned_specialists=json.dumps(assigned),
    )

    db.add(db_case)
    await db.commit()
    await db.refresh(db_case)
    return _to_case_response(db_case)


@router.get("/list", response_model=List[Case])
async def list_cases(skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_db)):
    """Lister tous les cas"""
    result = await db.execute(select(CaseDB).offset(skip).limit(limit))
    cases = result.scalars().all()
    return [_to_case_response(c) for c in cases]


@router.get("/{case_id}", response_model=Case)
async def get_case(case_id: str, db: AsyncSession = Depends(get_db)):
    """Récupérer un cas par ID"""
    result = await db.execute(select(CaseDB).where(CaseDB.id == case_id))
    case = result.scalar_one_or_none()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    return _to_case_response(case)


@router.patch("/{case_id}/status")
async def update_case_status(case_id: str, status: CaseStatus, db: AsyncSession = Depends(get_db)):
    """Mettre à jour le statut d'un cas"""
    result = await db.execute(select(CaseDB).where(CaseDB.id == case_id))
    case = result.scalar_one_or_none()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    case.status = status
    await db.commit()
    await db.refresh(case)
    return {"message": "Case status updated", "case_id": case_id, "new_status": status}


@router.delete("/delete/{case_id}")
async def delete_case(case_id: str, db: AsyncSession = Depends(get_db)):
    # Charger le cas
    result = await db.execute(select(CaseDB).where(CaseDB.id == case_id))
    case = result.scalars().first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    await db.delete(case)
    await db.commit()
    return {"detail": "Case deleted", "id": case_id}