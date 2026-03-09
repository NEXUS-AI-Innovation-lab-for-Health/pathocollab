from __future__ import annotations

import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification import Notification, NotificationCreate, NotificationDB

logger = logging.getLogger(__name__)


class NotificationService:
    @staticmethod
    async def create_notification(db: AsyncSession, notification_data: NotificationCreate) -> Notification:
        db_notification = NotificationDB(**notification_data.model_dump())
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
        return Notification.model_validate(db_notification)
