from sqlalchemy.orm import Session
from app.models.notification import NotificationDB, NotificationCreate, Notification
import logging

logger = logging.getLogger(__name__)

class NotificationService:
    @staticmethod
    async def create_notification(db: Session, notification_data: NotificationCreate) -> Notification:
        """Créer une notification et la sauvegarder en base de données"""
        try:
            db_notification = NotificationDB(**notification_data.model_dump())
            db.add(db_notification)
            db.commit()
            db.refresh(db_notification)
            
            logger.info(f"Notification created: {db_notification.id} for user {db_notification.user_id}")
            return Notification.model_validate(db_notification)
        except Exception as e:
            logger.error(f"Failed to create notification: {e}")
            raise e
