from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timezone
import json
from typing import List

from app.models.workflow import Workflow, WorkflowCreate, WorkflowDB
from app.models.notification import NotificationCreate, NotificationType
from app.utils.database import get_db
from app.services.notification_service import NotificationService

router = APIRouter(prefix="/workflows", tags=["Workflows"])

@router.post("/", response_model=Workflow, status_code=status.HTTP_201_CREATED)
async def create_workflow(workflow_data: WorkflowCreate, db: AsyncSession = Depends(get_db)):
    """Créer un workflow pour un cas"""
    # Vérifier si un workflow existe déjà pour ce cas
    res = await db.execute(select(WorkflowDB).where(WorkflowDB.case_id == workflow_data.case_id))
    existing_workflow = res.scalars().first()
    if existing_workflow:
        return Workflow.model_validate(existing_workflow)

    # Spécialistes (déjà des emails)
    specialists_emails = list(workflow_data.specialists_order or [])

    db_workflow = WorkflowDB(
        case_id=workflow_data.case_id,
        specialists_order=json.dumps(specialists_emails),
        current_step=0,
        is_completed=False,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    db.add(db_workflow)
    await db.commit()
    await db.refresh(db_workflow)
    

    # Notifier le premier spécialiste
    if specialists_emails:
        first_specialist = specialists_emails[0]
        notification = NotificationCreate(
            user_id=first_specialist,
            case_id=workflow_data.case_id,
            type=NotificationType.TURN_READY,
            title="Nouveau cas assigné",
            message=f"Le cas {workflow_data.case_id} est maintenant à votre tour pour analyse.",
        )
        try:
            await NotificationService.create_notification(db, notification)
        except Exception as e:
            await db.rollback()
            print(f"Erreur lors de la création de la notification: {str(e)}")

    return Workflow.model_validate(db_workflow)

@router.get("/{workflow_id}", response_model=Workflow)
async def get_workflow(workflow_id: str, db: AsyncSession = Depends(get_db)):
    """Récupérer un workflow par son ID"""
    res = await db.execute(select(WorkflowDB).where(WorkflowDB.id == workflow_id))
    workflow = res.scalars().first()
    if not workflow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workflow avec l'ID {workflow_id} non trouvé",
        )
    return Workflow.model_validate(workflow)

@router.get("/case/{case_id}", response_model=Workflow)
async def get_workflow_by_case(case_id: str, db: AsyncSession = Depends(get_db)):
    """Récupérer le workflow d'un cas spécifique"""
    res = await db.execute(select(WorkflowDB).where(WorkflowDB.case_id == case_id))
    workflow = res.scalars().first()
    if not workflow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Aucun workflow trouvé pour le cas {case_id}",
        )
    return Workflow.model_validate(workflow)

@router.post("/{workflow_id}/advance", response_model=Workflow)
async def advance_workflow(workflow_id: str, db: AsyncSession = Depends(get_db)):
    """Avancer le workflow à l'étape suivante et notifier"""
    res = await db.execute(select(WorkflowDB).where(WorkflowDB.id == workflow_id))
    workflow = res.scalars().first()
    if not workflow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workflow avec l'ID {workflow_id} non trouvé",
        )

    if workflow.is_completed:
        return Workflow.model_validate(workflow)

    # Charger la liste des spécialistes
    try:
        specialists = json.loads(workflow.specialists_order or "[]")
    except json.JSONDecodeError:
        specialists = []

    workflow.current_step += 1
    workflow.updated_at = datetime.now(timezone.utc)

    if workflow.current_step >= len(specialists):
        workflow.is_completed = True
        workflow.completed_at = datetime.now(timezone.utc)

        for specialist_id in specialists:
            notification = NotificationCreate(
                user_id=specialist_id,
                case_id=workflow.case_id,
                type=NotificationType.CASE_COMPLETED,
                title="Cas complété",
                message=f"Le cas {workflow.case_id} a été finalisé. Rapport disponible.",
            )
            try:
                await NotificationService.create_notification(db, notification)
            except Exception as e:
                print(f"Erreur lors de la notification de complétion: {str(e)}")
    else:
        next_specialist = specialists[workflow.current_step]
        notification = NotificationCreate(
            user_id=next_specialist,
            case_id=workflow.case_id,
            type=NotificationType.TURN_READY,
            title="C'est votre tour",
            message=f"Le cas {workflow.case_id} est maintenant à votre tour pour analyse.",
        )
        try:
            await NotificationService.create_notification(db, notification)
        except Exception as e:
            print(f"Erreur lors de la notification de tour: {str(e)}")

    await db.commit()
    await db.refresh(workflow)
    return Workflow.model_validate(workflow)
