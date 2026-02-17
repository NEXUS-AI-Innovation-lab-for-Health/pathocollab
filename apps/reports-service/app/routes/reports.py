from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.models.report import Report, ReportCreate, ReportDB, ReportAssistRequest
# from app.services.ai_service import AIService  # Désactivé pour l'instant
from app.utils.database import get_db
from typing import List
from datetime import datetime, timezone

router = APIRouter(prefix="/reports", tags=["Reports"])
# ai_service = AIService()  # Désactivé pour l'instant

@router.post("/", response_model=Report, status_code=201)
def create_report(report_data: ReportCreate, db: Session = Depends(get_db)):
    """Créer un rapport"""
    db_report = ReportDB(**report_data.model_dump())
    db.add(db_report)
    db.commit()
    db.refresh(db_report)
    return Report.model_validate(db_report)

@router.post("/assist", status_code=200)
async def assist_report(request: ReportAssistRequest, db: Session = Depends(get_db)):
    """Générer un rapport assisté par IA - Désactivé pour l'instant"""
    try:
        # TODO: Implémenter l'IA quand le module sera disponible
        return {
            "success": False,
            "message": "Service IA temporairement désactivé",
            "generated_content": None
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating report: {str(e)}")

@router.get("/case/{case_id}", response_model=List[Report])
def get_case_reports(case_id: str, db: Session = Depends(get_db)):
    """Récupérer tous les rapports d'un cas"""
    reports = db.query(ReportDB).filter(ReportDB.case_id == case_id).order_by(ReportDB.created_at).all()
    return [Report.model_validate(r) for r in reports]

@router.get("/{report_id}", response_model=Report)
def get_report(report_id: str, db: Session = Depends(get_db)):
    """Récupérer un rapport par ID"""
    report = db.query(ReportDB).filter(ReportDB.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    return Report.model_validate(report)

@router.put("/{report_id}", response_model=Report)
def update_report(report_id: str, report_data: ReportCreate, db: Session = Depends(get_db)):
    """Mettre à jour un rapport"""
    report = db.query(ReportDB).filter(ReportDB.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    
    # Mettre à jour les champs
    report.title = report_data.title
    report.content = report_data.content
    report.is_final = report_data.is_final
    report.updated_at = datetime.now(timezone.utc)
    
    db.commit()
    db.refresh(report)
    return Report.model_validate(report)

@router.delete("/{report_id}")
def delete_report(report_id: str, db: Session = Depends(get_db)):
    """Supprimer un rapport"""
    report = db.query(ReportDB).filter(ReportDB.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    
    # Autoriser la suppression de tous les rapports (brouillons et finaux)
    db.delete(report)
    db.commit()
    return {"message": "Report deleted successfully", "report_id": report_id}

@router.patch("/{report_id}/finalize")
def finalize_report(report_id: str, db: Session = Depends(get_db)):
    """Marquer un rapport comme final"""
    report = db.query(ReportDB).filter(ReportDB.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    
    report.is_final = True
    db.commit()
    return {"message": "Report finalized", "report_id": report_id}
