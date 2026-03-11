from __future__ import annotations

import json
from datetime import datetime, timezone

from fastapi import APIRouter, Body, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification import NotificationCreate, NotificationType
from app.models.workflow import (
    OlgaTaskCompleteRequest,
    OlgaTasksResponse,
    Workflow,
    WorkflowCreate,
    WorkflowDB,
    WorkflowEngine,
)
from app.services.notification_service import NotificationService
from app.services.olga_client import OlgaClient
from app.utils.database import get_db

router = APIRouter(prefix="/workflows", tags=["Workflows"])


def _workflow_to_schema(workflow: WorkflowDB) -> Workflow:
    return Workflow.model_validate(workflow)


async def _get_workflow_or_404(db: AsyncSession, workflow_id: str) -> WorkflowDB:
    workflow = (await db.execute(select(WorkflowDB).where(WorkflowDB.id == workflow_id))).scalars().first()
    if not workflow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workflow avec l'ID {workflow_id} non trouvé",
        )
    return workflow


@router.post("/", response_model=Workflow, status_code=status.HTTP_201_CREATED)
async def create_workflow(
    workflow_data: WorkflowCreate,
    db: AsyncSession = Depends(get_db),
) -> Workflow:
    existing = (await db.execute(select(WorkflowDB).where(WorkflowDB.case_id == workflow_data.case_id))).scalars().first()
    if existing:
        return _workflow_to_schema(existing)

    db_workflow = WorkflowDB(
        case_id=workflow_data.case_id,
        specialists_order=json.dumps(workflow_data.specialists_order),
        current_step=0,
        workflow_engine=workflow_data.workflow_engine.value,
        olga_workflow_code=workflow_data.olga_workflow_code,
        is_completed=False,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    if workflow_data.workflow_engine == WorkflowEngine.OLGA:
        olga_client = OlgaClient()
        try:
            session = await olga_client.create_session(
                workflow_code=workflow_data.olga_workflow_code or "",
                data={"case_id": workflow_data.case_id},
            )
        except Exception as exc:
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc

        db_workflow.olga_session_id = (
            session.get("id")
            or session.get("sessionId")
            or session.get("session_id")
        )
        db_workflow.olga_status = session.get("status", "created")

    db.add(db_workflow)
    await db.commit()
    await db.refresh(db_workflow)

    if workflow_data.workflow_engine == WorkflowEngine.LOCAL and workflow_data.specialists_order:
        first_specialist = workflow_data.specialists_order[0]
        await NotificationService.create_notification(
            db,
            NotificationCreate(
                user_id=first_specialist,
                case_id=workflow_data.case_id,
                type=NotificationType.TURN_READY,
                title="Nouveau cas assigné",
                message=f"Le cas {workflow_data.case_id} est maintenant à votre tour pour analyse.",
            ),
        )

    return _workflow_to_schema(db_workflow)


@router.get("/{workflow_id}", response_model=Workflow)
async def get_workflow(workflow_id: str, db: AsyncSession = Depends(get_db)) -> Workflow:
    workflow = await _get_workflow_or_404(db, workflow_id)
    return _workflow_to_schema(workflow)


@router.get("/case/{case_id}", response_model=Workflow)
async def get_workflow_by_case(case_id: str, db: AsyncSession = Depends(get_db)) -> Workflow:
    workflow = (await db.execute(select(WorkflowDB).where(WorkflowDB.case_id == case_id))).scalars().first()
    if not workflow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Aucun workflow trouvé pour le cas {case_id}",
        )
    return _workflow_to_schema(workflow)


@router.post("/{workflow_id}/advance", response_model=Workflow)
async def advance_workflow(workflow_id: str, db: AsyncSession = Depends(get_db)) -> Workflow:
    workflow = await _get_workflow_or_404(db, workflow_id)

    if workflow.workflow_engine != WorkflowEngine.LOCAL.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="advance n'est disponible que pour les workflows locaux",
        )

    if workflow.is_completed:
        return _workflow_to_schema(workflow)

    specialists = workflow.specialists_as_list()
    workflow.current_step += 1
    workflow.updated_at = datetime.now(timezone.utc)

    if workflow.current_step >= len(specialists):
        workflow.is_completed = True
        workflow.completed_at = datetime.now(timezone.utc)

        await db.commit()
        await db.refresh(workflow)

        for specialist_id in specialists:
            await NotificationService.create_notification(
                db,
                NotificationCreate(
                    user_id=specialist_id,
                    case_id=workflow.case_id,
                    type=NotificationType.CASE_COMPLETED,
                    title="Cas complété",
                    message=f"Le cas {workflow.case_id} a été finalisé. Rapport disponible.",
                ),
            )
    else:
        await db.commit()
        await db.refresh(workflow)

        next_specialist = specialists[workflow.current_step]
        await NotificationService.create_notification(
            db,
            NotificationCreate(
                user_id=next_specialist,
                case_id=workflow.case_id,
                type=NotificationType.TURN_READY,
                title="C'est votre tour",
                message=f"Le cas {workflow.case_id} est maintenant à votre tour pour analyse.",
            ),
        )

    return _workflow_to_schema(workflow)


@router.get("/{workflow_id}/olga/tasks", response_model=OlgaTasksResponse)
async def get_olga_tasks(
    workflow_id: str,
    db: AsyncSession = Depends(get_db),
) -> OlgaTasksResponse:
    workflow = await _get_workflow_or_404(db, workflow_id)

    if workflow.workflow_engine != WorkflowEngine.OLGA.value:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Ce workflow n'utilise pas Olga")
    if not workflow.olga_session_id:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Aucune session Olga liée à ce workflow")

    olga_client = OlgaClient()
    try:
        tasks = await olga_client.get_tasks(workflow.olga_session_id)
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc

    return OlgaTasksResponse(
        workflow_id=workflow.id,
        session_id=workflow.olga_session_id,
        tasks=tasks,
    )


@router.post("/{workflow_id}/olga/tasks/{task_id}/complete")
async def complete_olga_task(
    workflow_id: str,
    task_id: str,
    payload: OlgaTaskCompleteRequest = Body(...),
    db: AsyncSession = Depends(get_db),
) -> dict:
    workflow = await _get_workflow_or_404(db, workflow_id)

    if workflow.workflow_engine != WorkflowEngine.OLGA.value:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Ce workflow n'utilise pas Olga")

    olga_client = OlgaClient()
    try:
        result = await olga_client.complete_task(task_id, payload.data)
        session = await olga_client.get_session(workflow.olga_session_id) if workflow.olga_session_id else {}
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc

    workflow.olga_status = session.get("status", workflow.olga_status)
    if str(workflow.olga_status).lower() in {"completed", "done", "finished"}:
        workflow.is_completed = True
        workflow.completed_at = datetime.now(timezone.utc)
    workflow.updated_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(workflow)

    return {
        "message": "Tâche Olga complétée",
        "workflow_id": workflow.id,
        "olga_result": result,
        "olga_status": workflow.olga_status,
        "is_completed": workflow.is_completed,
    }
