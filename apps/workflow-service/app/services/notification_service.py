from __future__ import annotations

import logging

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification import Notification, NotificationCreate, NotificationDB

logger = logging.getLogger(__name__)


class NotificationService:
    @staticmethod
    def _to_notification_response(db_notification: NotificationDB) -> Notification:
        return Notification(
            id=db_notification.id,
            user_id=db_notification.user_id,
            case_id=db_notification.case_id,
            type=db_notification.notification_type,
            title=db_notification.title,
            message=db_notification.message,
            is_read=db_notification.is_read,
            created_at=db_notification.created_at,
        )

    @staticmethod
    async def create_notification(db: AsyncSession, notification_data: NotificationCreate) -> Notification:
        db_notification = NotificationDB(
            user_id=notification_data.user_id,
            case_id=notification_data.case_id,
            notification_type=notification_data.type,
            title=notification_data.title,
            message=notification_data.message,
        )

        db.add(db_notification)
        await db.flush()
        await db.commit()
        await db.refresh(db_notification)

        logger.info(
            "Notification created",
            extra={
                "notification_id": db_notification.id,
                "user_id": db_notification.user_id,
                "case_id": db_notification.case_id,
            },
        )

        return NotificationService._to_notification_response(db_notification)

    @staticmethod
    async def list_user_notifications(db: AsyncSession, user_id: str) -> list[NotificationDB]:
        result = await db.execute(
            select(NotificationDB)
            .where(NotificationDB.user_id == user_id)
            .order_by(NotificationDB.created_at.desc())
        )
        return list(result.scalars().all())

    @staticmethod
    async def count_unread_notifications(db: AsyncSession, user_id: str) -> int:
        result = await db.execute(
            select(func.count(NotificationDB.id)).where(
                NotificationDB.user_id == user_id,
                NotificationDB.is_read == False,  # noqa: E712
            )
        )
        count = result.scalar_one()
        return int(count or 0)

    @staticmethod
    async def mark_as_read(db: AsyncSession, notification_id: str) -> dict:
        result = await db.execute(
            select(NotificationDB).where(NotificationDB.id == notification_id)
        )
        notification = result.scalar_one_or_none()

        if notification is None:
            return {
                "success": False,
                "message": "Notification not found",
                "notification_id": notification_id,
                "unread_count": 0,
            }

        # idempotent : si déjà lu, on ne redécrémente pas côté logique
        if not notification.is_read:
            notification.is_read = True
            await db.commit()
            await db.refresh(notification)

        unread_count = await NotificationService.count_unread_notifications(
            db, notification.user_id
        )

        return {
            "success": True,
            "message": "Notification marked as read",
            "notification_id": notification_id,
            "unread_count": unread_count,
        }