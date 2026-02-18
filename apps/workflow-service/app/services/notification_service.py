from __future__ import annotations

import logging
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification import NotificationDB, NotificationCreate, Notification

logger = logging.getLogger(__name__)

class NotificationService:
    @staticmethod
    async def create_notification(db: AsyncSession, notification_data: NotificationCreate) -> Notification:
        """Créer une notification et la sauvegarder en base de données"""
        try:
            db_notification = NotificationDB(**notification_data.model_dump())
            db.add(db_notification)
            await db.commit()
            await db.refresh(db_notification)

            logger.info(f"Notification created: {db_notification.id} for user {db_notification.user_id}")
            return Notification.model_validate(db_notification)
        except Exception as e:
            logger.error(f"Failed to create notification: {e}")
            raise
