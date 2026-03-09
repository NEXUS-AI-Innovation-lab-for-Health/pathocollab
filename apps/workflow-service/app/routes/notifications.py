from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification import (
    Notification,
    NotificationCreate,
    NotificationDB,
    NotificationListResponse,
    NotificationReadResponse,
)
from app.services.notification_service import NotificationService
from app.utils.database import get_db

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.post("/", response_model=Notification, status_code=status.HTTP_201_CREATED)
async def create_notification(
    notification_data: NotificationCreate,
    db: AsyncSession = Depends(get_db),
) -> Notification:
    return await NotificationService.create_notification(db, notification_data)


@router.get("/user/{user_id}", response_model=NotificationListResponse)
async def get_user_notifications(
    user_id: str,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
) -> NotificationListResponse:
    stmt = (
        select(NotificationDB)
        .where(NotificationDB.user_id == user_id)
        .order_by(NotificationDB.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    count_stmt = select(func.count()).select_from(NotificationDB).where(NotificationDB.user_id == user_id)

    notifications = (await db.execute(stmt)).scalars().all()
    total = (await db.execute(count_stmt)).scalar_one()

    return NotificationListResponse(
        items=[Notification.model_validate(item) for item in notifications],
        total=total,
    )


@router.patch("/{notification_id}/read", response_model=NotificationReadResponse)
async def mark_as_read(
    notification_id: str,
    db: AsyncSession = Depends(get_db),
) -> NotificationReadResponse:
    stmt = (
        update(NotificationDB)
        .where(NotificationDB.id == notification_id)
        .values(is_read=True)
        .execution_options(synchronize_session="fetch")
    )
    result = await db.execute(stmt)
    await db.commit()

    if not result.rowcount:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")

    return NotificationReadResponse(message="Notification marked as read")
