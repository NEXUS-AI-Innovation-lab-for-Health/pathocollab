from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app.models.patient import Patient, PatientCreate, PatientDB
from app.utils.database import get_db

router = APIRouter(prefix="/patients", tags=["Patients"])


@router.post("/create", response_model=Patient, status_code=status.HTTP_201_CREATED)
async def create_patient(patient_data: PatientCreate, db: AsyncSession = Depends(get_db)):
    db_patient = PatientDB(**patient_data.model_dump())
    db.add(db_patient)
    await db.commit()
    await db.refresh(db_patient)
    return Patient.model_validate(db_patient)


@router.get("/list", response_model=List[Patient])
async def list_patients(skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(PatientDB).offset(skip).limit(limit))
    patients = result.scalars().all()
    return [Patient.model_validate(p) for p in patients]


@router.get("/{patient_id}", response_model=Patient)
async def get_patient(patient_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(PatientDB).where(PatientDB.id == patient_id))
    patient = result.scalar_one_or_none()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    return Patient.model_validate(patient)


@router.delete("/delete/{patient_id}")
async def delete_patient(patient_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(PatientDB).where(PatientDB.id == patient_id))
    patient = result.scalars().first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    await db.delete(patient)
    await db.commit()
    return {"detail": "Patient deleted", "id": patient_id}


@router.delete("/delete/all")
async def delete_all_patients(db: AsyncSession = Depends(get_db)):
    await db.execute(delete(PatientDB))
    await db.commit()
    return {"detail": "All patients deleted"}