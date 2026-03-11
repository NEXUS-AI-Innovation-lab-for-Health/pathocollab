from __future__ import annotations

import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification import Notification, NotificationCreate, NotificationDB

logger = logging.getLogger(__name__)


class NotificationService:
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