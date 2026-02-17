from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.models.workflow import Workflow, WorkflowCreate, WorkflowDB, WorkflowBase
from app.models.notification import NotificationCreate, NotificationType
from app.utils.database import get_db
from app.services.notification_service import NotificationService
from datetime import datetime, timezone
import json
from typing import List, Optional

router = APIRouter(prefix="/workflows", tags=["Workflows"])

@router.post("/", response_model=Workflow, status_code=status.HTTP_201_CREATED)
async def create_workflow(workflow_data: WorkflowCreate, db: Session = Depends(get_db)):
    """Créer un workflow pour un cas"""
    # Vérifier si un workflow existe déjà pour ce cas
    existing_workflow = db.query(WorkflowDB).filter(WorkflowDB.case_id == workflow_data.case_id).first()
    if existing_workflow:
        return Workflow.from_orm(existing_workflow)
    
    # Utiliser directement les spécialistes (déjà des emails)
    specialists_emails = workflow_data.specialists_order
    
    # Créer le nouveau workflow
    db_workflow = WorkflowDB(
        case_id=workflow_data.case_id,
        specialists_order=json.dumps(specialists_emails),
        current_step=0,
        is_completed=False,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )
    
    db.add(db_workflow)
    db.commit()
    db.refresh(db_workflow)
    
    # Notifier le premier spécialiste
    if specialists_emails:
        first_specialist = specialists_emails[0]
        notification = NotificationCreate(
            user_id=first_specialist,
            case_id=workflow_data.case_id,
            type=NotificationType.TURN_READY,
            title="Nouveau cas assigné",
            message=f"Le cas {workflow_data.case_id} est maintenant à votre tour pour analyse."
        )
        try:
            await NotificationService.create_notification(db, notification)
        except Exception as e:
            # Ne pas échouer la création du workflow si la notification échoue
            print(f"Erreur lors de la création de la notification: {str(e)}")
    
    return Workflow.from_orm(db_workflow)

@router.get("/{workflow_id}", response_model=Workflow)
def get_workflow(workflow_id: str, db: Session = Depends(get_db)):
    """Récupérer un workflow par son ID"""
    workflow = db.query(WorkflowDB).filter(WorkflowDB.id == workflow_id).first()
    if not workflow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workflow avec l'ID {workflow_id} non trouvé"
        )
    return Workflow.from_orm(workflow)

@router.get("/case/{case_id}", response_model=Workflow)
def get_workflow_by_case(case_id: str, db: Session = Depends(get_db)):
    """Récupérer le workflow d'un cas spécifique"""
    workflow = db.query(WorkflowDB).filter(WorkflowDB.case_id == case_id).first()
    if not workflow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Aucun workflow trouvé pour le cas {case_id}"
        )
    return Workflow.from_orm(workflow)

@router.post("/{workflow_id}/advance", response_model=Workflow)
async def advance_workflow(workflow_id: str, db: Session = Depends(get_db)):
    """
    Avancer le workflow à l'étape suivante
    
    - Incrémente le compteur d'étapes
    - Si c'était la dernière étape, marque le workflow comme terminé
    - Notifie les utilisateurs concernés
    """
    workflow = db.query(WorkflowDB).filter(WorkflowDB.id == workflow_id).first()
    if not workflow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workflow avec l'ID {workflow_id} non trouvé"
        )
    
    if workflow.is_completed:
        return Workflow.from_orm(workflow)
    
    # Charger la liste des spécialistes
    try:
        specialists = json.loads(workflow.specialists_order)
    except json.JSONDecodeError:
        specialists = []
    
    # Avancer d'une étape
    workflow.current_step += 1
    workflow.updated_at = datetime.now(timezone.utc)
    
    # Vérifier si toutes les étapes sont terminées
    if workflow.current_step >= len(specialists):
        workflow.is_completed = True
        workflow.completed_at = datetime.now(timezone.utc)
        
        # Notifier tous les spécialistes de la complétion
        for specialist_id in specialists:
            notification = NotificationCreate(
                user_id=specialist_id,
                case_id=workflow.case_id,
                type=NotificationType.CASE_COMPLETED,
                title="Cas complété",
                message=f"Le cas {workflow.case_id} a été finalisé. Rapport disponible."
            )
            try:
                await NotificationService.create_notification(db, notification)
            except Exception as e:
                print(f"Erreur lors de la notification de complétion: {str(e)}")
    else:
        # Notifier le prochain spécialiste
        next_specialist = specialists[workflow.current_step]
        notification = NotificationCreate(
            user_id=next_specialist,
            case_id=workflow.case_id,
            type=NotificationType.TURN_READY,
            title="C'est votre tour",
            message=f"Le cas {workflow.case_id} est maintenant à votre tour pour analyse."
        )
        try:
            await NotificationService.create_notification(db, notification)
        except Exception as e:
            print(f"Erreur lors de la notification de tour: {str(e)}")
    
    db.commit()
    db.refresh(workflow)
    return Workflow.from_orm(workflow)
