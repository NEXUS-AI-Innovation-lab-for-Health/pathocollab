from __future__ import annotations

from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.report import Report, ReportCreate, ReportUpdate, ReportDB, ReportAssistRequest
from app.utils.database import get_db

router = APIRouter(prefix="/reports", tags=["Reports"])


@router.post("/", response_model=Report, status_code=201)
async def create_report(report_data: ReportCreate, db: AsyncSession = Depends(get_db)) -> Report:
    try:
        db_report = ReportDB(
            case_id=report_data.case_id,
            user_id=report_data.user_id,
            title=report_data.title,
            content=report_data.content,
            is_final=getattr(report_data, "is_final", False),
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        db.add(db_report)
        await db.commit()
        await db.refresh(db_report)

        # Pydantic v2
        if hasattr(Report, "model_validate"):
            return Report.model_validate(db_report)
        return Report.from_orm(db_report)  # type: ignore[attr-defined]

    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Erreur création report: {e}")


@router.get("/", response_model=List[Report])
async def list_reports(db: AsyncSession = Depends(get_db)) -> List[Report]:
    try:
        result = await db.execute(select(ReportDB).order_by(ReportDB.created_at.desc()))
        rows = result.scalars().all()

        if hasattr(Report, "model_validate"):
            return [Report.model_validate(r) for r in rows]
        return [Report.from_orm(r) for r in rows]  # type: ignore[attr-defined]

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur list reports: {e}")


@router.get("/case/{case_id}", response_model=List[Report])
async def list_reports_by_case(case_id: str, db: AsyncSession = Depends(get_db)) -> List[Report]:
    try:
        result = await db.execute(
            select(ReportDB).where(ReportDB.case_id == case_id).order_by(ReportDB.created_at.desc())
        )
        rows = result.scalars().all()

        if hasattr(Report, "model_validate"):
            return [Report.model_validate(r) for r in rows]
        return [Report.from_orm(r) for r in rows]  # type: ignore[attr-defined]

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur list reports par case: {e}")


@router.get("/{report_id}", response_model=Report)
async def get_report(report_id: str, db: AsyncSession = Depends(get_db)) -> Report:
    result = await db.execute(select(ReportDB).where(ReportDB.id == report_id))
    report = result.scalars().first()
    if not report:
        raise HTTPException(status_code=404, detail="Report introuvable")

    if hasattr(Report, "model_validate"):
        return Report.model_validate(report)
    return Report.from_orm(report)  # type: ignore[attr-defined]





@router.delete("/{report_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_report(report_id: str, db: AsyncSession = Depends(get_db)) -> Response:
    """Supprime un rapport."""
    try:
        result = await db.execute(select(ReportDB).where(ReportDB.id == report_id))
        report = result.scalars().first()
        if not report:
            raise HTTPException(status_code=404, detail="Report introuvable")

        await db.delete(report)
        await db.commit()
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Erreur suppression report: {e}")
@router.put("/{report_id}", response_model=Report)
async def update_report(report_id: str, payload: ReportUpdate, db: AsyncSession = Depends(get_db)) -> Report:
    """Met à jour un rapport existant (utilisé par le front)."""
    try:
        result = await db.execute(select(ReportDB).where(ReportDB.id == report_id))
        report = result.scalars().first()
        if not report:
            raise HTTPException(status_code=404, detail="Report introuvable")

        # Mise à jour partielle
        if payload.title is not None:
            report.title = payload.title
        if payload.content is not None:
            report.content = payload.content
        if payload.is_final is not None:
            report.is_final = payload.is_final

        report.updated_at = datetime.now(timezone.utc)

        db.add(report)
        await db.commit()
        await db.refresh(report)

        if hasattr(Report, "model_validate"):
            return Report.model_validate(report)
        return Report.from_orm(report)  # type: ignore[attr-defined]

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Erreur update report: {e}")


@router.patch("/{report_id}", response_model=Report)
async def patch_report(report_id: str, payload: ReportUpdate, db: AsyncSession = Depends(get_db)) -> Report:
    """Alias PATCH (même logique que PUT)."""
    return await update_report(report_id, payload, db)


# Endpoint optionnel (si tu as un service IA / assistance)
@router.post("/assist", response_model=Report)
async def assist_report(payload: ReportAssistRequest, db: AsyncSession = Depends(get_db)) -> Report:
    # Ici on ne touche pas à AIService (désactivé chez toi), mais on garde une structure saine.
    # Tu peux brancher AIService plus tard.
    result = await db.execute(select(ReportDB).where(ReportDB.id == payload.report_id))
    report = result.scalars().first()
    if not report:
        raise HTTPException(status_code=404, detail="Report introuvable")

    # Exemple: mise à jour simple (placeholder)
    report.updated_at = datetime.now(timezone.utc)

    db.add(report)
    await db.commit()
    await db.refresh(report)

    if hasattr(Report, "model_validate"):
        return Report.model_validate(report)
    return Report.from_orm(report)  # type: ignore[attr-defined]
