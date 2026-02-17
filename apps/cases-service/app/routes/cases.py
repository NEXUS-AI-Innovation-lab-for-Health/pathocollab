from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.models.case import Case, CaseCreate, CaseDB, CaseStatus
from app.utils.database import get_db
from typing import List
import json

router = APIRouter(prefix="/cases", tags=["Cases"])

def get_db_override():
    raise RuntimeError("get_db not injected")

def get_current_user_override():
    raise RuntimeError("current_user not injected")

def router_api():
    return router

@router.post("/", response_model=Case, status_code=status.HTTP_201_CREATED)
def create_case(case_data: CaseCreate, db: Session = Depends(get_db)):
    """Créer un nouveau cas de biopsie"""
    db_case = CaseDB(
        **{k: v for k, v in case_data.model_dump().items() if k != 'assigned_specialists'},
        assigned_specialists=json.dumps(case_data.assigned_specialists)
    )
    db.add(db_case)
    db.commit()
    db.refresh(db_case)
    
    case_dict = {
        'id': db_case.id,
        'patient_id': db_case.patient_id,
        'title': db_case.title,
        'description': db_case.description,
        'status': db_case.status,
        'created_by': db_case.created_by,
        'assigned_specialists': json.loads(db_case.assigned_specialists) if db_case.assigned_specialists else [],
        'created_at': db_case.created_at,
        'completed_at': db_case.completed_at
    }
    return Case(**case_dict)

@router.get("/", response_model=List[Case])
def list_cases(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """Lister tous les cas"""
    cases = db.query(CaseDB).offset(skip).limit(limit).all()
    result = []
    for c in cases:
        case_dict = {
            'id': c.id,
            'patient_id': c.patient_id,
            'title': c.title,
            'description': c.description,
            'status': c.status,
            'created_by': c.created_by,
            'assigned_specialists': json.loads(c.assigned_specialists) if c.assigned_specialists else [],
            'created_at': c.created_at,
            'completed_at': c.completed_at
        }
        result.append(Case(**case_dict))
    return result

@router.get("/{case_id}", response_model=Case)
def get_case(case_id: str, db: Session = Depends(get_db)):
    """Récupérer un cas par ID"""
    case = db.query(CaseDB).filter(CaseDB.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    
    case_dict = {
        'id': case.id,
        'patient_id': case.patient_id,
        'title': case.title,
        'description': case.description,
        'status': case.status,
        'created_by': case.created_by,
        'assigned_specialists': json.loads(case.assigned_specialists) if case.assigned_specialists else [],
        'created_at': case.created_at,
        'completed_at': case.completed_at
    }
    return Case(**case_dict)

@router.patch("/{case_id}/status")
def update_case_status(case_id: str, status: CaseStatus, db: Session = Depends(get_db)):
    """Mettre à jour le statut d'un cas"""
    case = db.query(CaseDB).filter(CaseDB.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    
    case.status = status
    db.commit()
    return {"message": "Case status updated", "case_id": case_id, "new_status": status}
