from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.models.patient import Patient, PatientCreate, PatientDB
from app.utils.database import get_db
from typing import List

router = APIRouter(prefix="/patients", tags=["Patients"])

def get_db_override():
    raise RuntimeError("get_db not injected")

def get_current_user_override():
    raise RuntimeError("current_user not injected")

def router_api():
    return router

@router.post("/", response_model=Patient, status_code=status.HTTP_201_CREATED)
def create_patient(patient_data: PatientCreate, db: Session = Depends(get_db)):
    """Créer un nouveau dossier patient"""
    db_patient = PatientDB(**patient_data.model_dump())
    db.add(db_patient)
    db.commit()
    db.refresh(db_patient)
    return Patient.model_validate(db_patient)

@router.get("/", response_model=List[Patient])
def list_patients(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """Lister tous les patients"""
    patients = db.query(PatientDB).offset(skip).limit(limit).all()
    return [Patient.model_validate(p) for p in patients]

@router.get("/{patient_id}", response_model=Patient)
def get_patient(patient_id: str, db: Session = Depends(get_db)):
    """Récupérer un patient par ID"""
    patient = db.query(PatientDB).filter(PatientDB.id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    return Patient.model_validate(patient)
