from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from typing import List

from app.models.notification import Notification, NotificationCreate, NotificationDB
from app.services.notification_service import NotificationService
from app.utils.database import get_db

router = APIRouter(prefix="/notifications", tags=["Notifications"])

@router.post("/", response_model=Notification, status_code=201)
async def create_notification(notification_data: NotificationCreate, db: AsyncSession = Depends(get_db)):
    """Créer une notification"""
    return await NotificationService.create_notification(db, notification_data)

@router.get("/user/{user_id}", response_model=List[Notification])
async def get_user_notifications(user_id: str, skip: int = 0, limit: int = 50, db: AsyncSession = Depends(get_db)):
    """Récupérer les notifications d'un utilisateur"""
    stmt = (
        select(NotificationDB)
        .where(NotificationDB.user_id == user_id)
        .order_by(NotificationDB.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    res = await db.execute(stmt)
    notifications = res.scalars().all()

    return [Notification.model_validate(n) for n in notifications]

@router.patch("/{notification_id}/read")
async def mark_as_read(notification_id: str, db: AsyncSession = Depends(get_db)):
    """Marquer une notification comme lue"""
    # update + check affected rows
    stmt = (
        update(NotificationDB)
        .where(NotificationDB.id == notification_id)
        .values(is_read=True)
        .execution_options(synchronize_session="fetch")
    )
    res = await db.execute(stmt)
    await db.commit()

    if res.rowcount and res.rowcount > 0:
        return {"message": "Notification marked as read"}
    raise HTTPException(status_code=404, detail="Notification not found")
