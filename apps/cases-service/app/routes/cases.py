from fastapi import APIRouter, Depends, HTTPException, status, Header
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app.models.case import Case, CaseCreate, CaseDB, CaseStatus
from app.utils.database import get_db
import os
from datetime import datetime, timezone

import json
import base64
import httpx

router = APIRouter(prefix="/cases", tags=["Cases"])


REPORTS_SERVICE_URL = os.getenv("REPORTS_SERVICE_URL", "http://reports-service:8005")


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

    # accès si créateur ou spécialiste assigné
    return (
        created_by in user_identities
        or bool(user_identities.intersection(assigned_specialists))
    )


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

    if not assigned_set:
        return db_case

    try:
        reports = await _extract_reports_for_case(db_case.id)
    except Exception:
        # On ne bloque pas le service des cas si reports-service est indisponible
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
    return {"message": "Case status updated", "case_id": case_id, "new_status": status}


@router.delete("/delete/{case_id}")
async def delete_case(case_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(CaseDB).where(CaseDB.id == case_id))
    case = result.scalars().first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    await db.delete(case)
    await db.commit()
    return {"detail": "Case deleted", "id": case_id}


@router.post("/{case_id}/sync-completion")
async def sync_case_completion(case_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(CaseDB).where(CaseDB.id == case_id))
    case = result.scalar_one_or_none()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    case = await _sync_case_completion(db, case)

    return {
        "case_id": case.id,
        "status": case.status,
        "completed_at": case.completed_at,
    }