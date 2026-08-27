from fastapi import APIRouter, Depends, HTTPException, status, Header
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

from app.models.case import Case, CaseCreate, CaseDB, CaseStatus
from app.utils.database import get_db
import os
from datetime import datetime, timezone

import json
import base64
import httpx
import logging

router = APIRouter(prefix="/cases", tags=["Cases"])


router = APIRouter(prefix="/cases", tags=["Cases"])

logger = logging.getLogger(__name__)

REPORTS_SERVICE_URL = os.getenv("REPORTS_SERVICE_URL", "http://reports-service:8005")
WORKFLOW_SERVICE_URL = os.getenv("WORKFLOW_SERVICE_URL", "http://workflow-service:8003")


def _normalize_identity(value: str | None) -> str:
    return (value or "").strip().lower()

def _user_identities(current_user) -> set[str]:
    identities = set()

    if isinstance(current_user, dict):
        identities.update(
            _normalize_identity(v)
            for v in [
                current_user.get("email"),
                current_user.get("sub"),
                current_user.get("username"),
                current_user.get("full_name"),
                current_user.get("name"),
                current_user.get("id"),
            ]
            if v
        )
    else:
        identities.update(
            _normalize_identity(v)
            for v in [
                getattr(current_user, "email", None),
                getattr(current_user, "sub", None),
                getattr(current_user, "username", None),
                getattr(current_user, "full_name", None),
                getattr(current_user, "name", None),
                getattr(current_user, "id", None),
            ]
            if v
        )

    return {v for v in identities if v}


def _user_role(current_user) -> str:
    if isinstance(current_user, dict):
        return _normalize_identity(current_user.get("role"))
    return _normalize_identity(getattr(current_user, "role", None))


def can_access_case(current_user, db_case: CaseDB) -> bool:
    role = _user_role(current_user)

    # Admin : accès total
    if role == "admin":
        return True

    user_identities = _user_identities(current_user)

    if not user_identities:
        return False

    created_by = _normalize_identity(db_case.created_by)

    assigned_specialists = {
        _normalize_identity(value)
        for value in (db_case.assigned_specialists or [])
        if value
    }

    # Accès classique PathoCollab
    if created_by in user_identities:
        return True

    if user_identities.intersection(assigned_specialists):
        return True

    # Accès service externe OncoCollab aux cas créés par intégration
    external_service_users = {
        _normalize_identity(value)
        for value in os.getenv(
            "EXTERNAL_SERVICE_USERS",
            "oncocollab-service@hospital.fr"
        ).split(",")
        if value.strip()
    }

    if (
        created_by in {"external", "oncocollab"}
        and user_identities.intersection(external_service_users)
    ):
        return True

    return False


async def _extract_reports_for_case(case_id: str) -> list[dict]:
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(f"{REPORTS_SERVICE_URL}/api/reports/case/{case_id}")
        response.raise_for_status()
        data = response.json()

    if isinstance(data, list):
        return data

    if isinstance(data, dict):
        if isinstance(data.get("items"), list):
            return data["items"]
        if isinstance(data.get("reports"), list):
            return data["reports"]

    return []


async def _sync_case_completion(db: AsyncSession, db_case: CaseDB) -> CaseDB:
    assigned_specialists = db_case.assigned_specialists or []
    assigned_set = {
        _normalize_identity(value)
        for value in assigned_specialists
        if value
    }

    if db_case.status == CaseStatus.CLOSED:
        return db_case

    if not assigned_set:
        return db_case

    try:
        reports = await _extract_reports_for_case(db_case.id)
    except Exception as exc:
        logger.warning("Impossible de récupérer les rapports pour %s: %s", db_case.id, exc)
        return db_case

    final_report_users = {
        _normalize_identity(report.get("user_id"))
        for report in reports
        if report.get("is_final") is True and report.get("user_id")
    }

    if assigned_set.issubset(final_report_users):
        if db_case.status != CaseStatus.COMPLETED:
            db_case.status = CaseStatus.COMPLETED
            db_case.completed_at = datetime.now(timezone.utc)
            await db.commit()
            await db.refresh(db_case)

    return db_case


def get_db_override():
    raise RuntimeError("get_db not injected")


def _decode_jwt_payload(token: str) -> dict:
    try:
        parts = token.split(".")
        if len(parts) != 3:
            raise ValueError("Invalid JWT format")

        payload_b64 = parts[1]
        padding = "=" * (-len(payload_b64) % 4)
        payload_bytes = base64.urlsafe_b64decode(payload_b64 + padding)
        payload = json.loads(payload_bytes.decode("utf-8"))

        if not isinstance(payload, dict):
            raise ValueError("Invalid JWT payload")

        return payload
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {str(e)}")


def get_current_user_override(authorization: str | None = Header(default=None)):
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing Authorization header")

    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid Authorization header")

    token = authorization.removeprefix("Bearer ").strip()
    payload = _decode_jwt_payload(token)

    return {
        "sub": payload.get("sub"),
        "email": payload.get("email") or payload.get("sub"),
        "username": payload.get("username"),
        "full_name": payload.get("full_name") or payload.get("name"),
        "name": payload.get("name"),
        "role": payload.get("role", "user"),
        "id": payload.get("id"),
    }


def router_api():
    return router


def _to_case_response(db_case: CaseDB) -> Case:
    return Case(
        id=db_case.id,
        patient_id=db_case.patient_id,
        title=db_case.title,
        description=db_case.description,
        status=db_case.status,
        created_by=db_case.created_by,
        assigned_specialists=db_case.assigned_specialists or [],
        created_at=db_case.created_at,
        completed_at=db_case.completed_at,
    )


@router.post("/create", response_model=Case, status_code=status.HTTP_201_CREATED)
async def create_case(
    case_data: CaseCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user_override),
):
    creator = (
        current_user.get("email")
        or current_user.get("sub")
        or current_user.get("full_name")
        or current_user.get("name")
        or ""
    )

    payload = case_data.model_dump()
    payload["created_by"] = creator

    db_case = CaseDB(**payload)

    db.add(db_case)
    await db.commit()
    await db.refresh(db_case)
    return _to_case_response(db_case)


@router.get("/list", response_model=List[Case])
async def list_cases(skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user_override)):
    result = await db.execute(select(CaseDB).offset(skip).limit(limit))
    cases = result.scalars().all()

    visible_cases = [c for c in cases if can_access_case(current_user, c)]

    return [_to_case_response(c) for c in visible_cases]

@router.get("/{case_id}", response_model=Case)
async def get_case(case_id: str, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user_override)):
    result = await db.execute(select(CaseDB).where(CaseDB.id == case_id))
    case = result.scalar_one_or_none()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    if not can_access_case(current_user, case):
        raise HTTPException(status_code=403, detail="Access denied")

    case = await _sync_case_completion(db, case)
    return _to_case_response(case)


@router.patch("/{case_id}/status")
async def update_case_status(case_id: str, status: CaseStatus, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(CaseDB).where(CaseDB.id == case_id))
    case = result.scalar_one_or_none()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    case.status = status
    await db.commit()
    await db.refresh(case)
    ensure_case_not_closed(case)
    return {"message": "Case status updated", "case_id": case_id, "new_status": status}


@router.delete("/delete/{case_id}")
async def delete_case(case_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(CaseDB).where(CaseDB.id == case_id))
    case = result.scalars().first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    await db.delete(case)
    await db.commit()
    ensure_case_not_closed(case)
    return {"detail": "Case deleted", "id": case_id}


@router.post("/{case_id}/sync-completion")
async def sync_case_completion(case_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(CaseDB).where(CaseDB.id == case_id))
    case_obj = result.scalars().first()

    if not case_obj:
        raise HTTPException(status_code=404, detail="Cas introuvable")

    async with httpx.AsyncClient(timeout=10.0) as client:
        reports_res = await client.get(f"{REPORTS_SERVICE_URL}/api/reports/case/{case_id}")
        reports_res.raise_for_status()
        reports = reports_res.json()

    if not reports:
        return {
            "case_id": case_id,
            "completed": False,
            "reason": "Aucun rapport"
        }

    all_final = all(report.get("is_final") is True for report in reports)

    if not all_final:
        return {
            "case_id": case_id,
            "completed": False,
            "reason": "Tous les rapports ne sont pas finalisés"
        }

    if case_obj.status != CaseStatus.COMPLETED:
        case_obj.status = CaseStatus.COMPLETED
        case_obj.completed_at = datetime.now(timezone.utc)
        db.add(case_obj)
        await db.commit()
        await db.refresh(case_obj)

    generalist_user = case_obj.created_by
    generalist_notified = False

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                f"{WORKFLOW_SERVICE_URL}/api/notifications",
                json={
                    "user_id": generalist_user,
                    "case_id": case_id,
                    "title": "Cas complété",
                    "message": f"Le cas {case_id} est terminé. Vous pouvez relire les rapports, générer le PDF final et fermer le cas."
                },
            )
            generalist_notified = response.status_code < 400
    except Exception as exc:
        logger.exception("Erreur création notification fin de cas %s: %s", case_id, exc)

    return {
        "case_id": case_id,
        "completed": True,
        "status": case_obj.status.value if hasattr(case_obj.status, "value") else case_obj.status,
        "generalist_notified": generalist_notified,
    }


class CloseCasePayload(BaseModel):
    closed_by: str

def ensure_case_not_closed(case: CaseDB):
    if case.status == CaseStatus.CLOSED:
        raise HTTPException(
            status_code=400,
            detail="Ce cas est fermé et ne peut plus être modifié"
        )

@router.post("/{case_id}/close")
async def close_case(
    case_id: str,
    payload: CloseCasePayload,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user_override),
):
    result = await db.execute(select(CaseDB).where(CaseDB.id == case_id))
    case_obj = result.scalars().first()

    if not case_obj:
        raise HTTPException(status_code=404, detail="Cas introuvable")

    if case_obj.status != CaseStatus.COMPLETED:
        raise HTTPException(
            status_code=400,
            detail="Le cas doit être terminé avant de pouvoir être fermé"
        )

    current_identities = _user_identities(current_user)
    creator_identity = _normalize_identity(case_obj.created_by)
    closed_by_identity = _normalize_identity(payload.closed_by)
    role = _user_role(current_user)

    if role != "medecin_generaliste" and role != "admin":
        raise HTTPException(
            status_code=403,
            detail="Seul un médecin généraliste peut fermer le cas"
        )

    if role != "admin":
        if creator_identity not in current_identities and closed_by_identity not in current_identities:
            raise HTTPException(
                status_code=403,
                detail="Seul le médecin généraliste créateur peut fermer le cas"
            )

    case_obj.status = CaseStatus.CLOSED
    db.add(case_obj)
    await db.commit()
    await db.refresh(case_obj)

    return {
        "id": case_obj.id,
        "status": case_obj.status.value if hasattr(case_obj.status, "value") else case_obj.status,
        "closed_by": payload.closed_by,
    }



# Partie External Pour Intégration 

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from app.models.patient import PatientDB


class ExternalPatientPayload(BaseModel):
    id: Optional[str] = None
    full_name: str
    age: int
    gender: str
    date_of_birth: Optional[str] = None
    medical_history: Optional[str] = ""
    symptoms: Optional[str] = ""
    imaging_notes: Optional[str] = ""


class ExternalCaseCreate(BaseModel):
    source: Optional[str] = "external"
    external_reference: Optional[str] = None
    patient: ExternalPatientPayload
    title: str
    description: Optional[str] = ""
    specialists_order: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


@router.post("/external", status_code=status.HTTP_201_CREATED)
async def create_external_case(
    payload: ExternalCaseCreate,
    db: AsyncSession = Depends(get_db),
):
    patient_id = payload.patient.id or f"PAT-EXT-{datetime.now().timestamp()}"

    result = await db.execute(select(PatientDB).where(PatientDB.id == patient_id))
    patient = result.scalar_one_or_none()

    if not patient:
        patient = PatientDB(
            id=patient_id,
            full_name=payload.patient.full_name,
            age=payload.patient.age,
            gender=payload.patient.gender,
            date_of_birth=payload.patient.date_of_birth,
            medical_history=payload.patient.medical_history,
            symptoms=payload.patient.symptoms,
            imaging_notes=payload.patient.imaging_notes,
        )
        db.add(patient)
        await db.flush()

    db_case = CaseDB(
        patient_id=patient.id,
        title=payload.title,
        description=payload.description,
        status=CaseStatus.PENDING,
        created_by=payload.source or "external",
        assigned_specialists=payload.specialists_order,
    )

    db.add(db_case)
    await db.commit()
    await db.refresh(db_case)

    workflow_created = False
    workflow_data = None

    if payload.specialists_order:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    f"{WORKFLOW_SERVICE_URL}/api/workflows/",
                    json={
                        "case_id": db_case.id,
                        "specialists_order": payload.specialists_order,
                        "workflow_engine": "local"
                    },
                )

                response.raise_for_status()
                workflow_data = response.json()
                workflow_created = True

        except Exception as exc:
            logger.exception(
                "Erreur création workflow pour le cas externe %s: %s",
                db_case.id,
                exc,
            )

    return {
        "case_id": db_case.id,
        "patient_id": patient.id,
        "embed_url": f"/embed/case/{db_case.id}",
        "status": "created",
        "specialists_order": payload.specialists_order,
        "workflow_created": workflow_created,
        "workflow": workflow_data,
    }


@router.get("/external/{case_id}")
async def get_external_case(
    case_id: str,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(CaseDB).where(CaseDB.id == case_id))
    db_case = result.scalar_one_or_none()

    if not db_case:
        raise HTTPException(status_code=404, detail="Case not found")

    return db_case