from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.models.notification import Notification, NotificationCreate, NotificationDB
from app.services.notification_service import NotificationService
from app.utils.database import get_db
from typing import List

router = APIRouter(prefix="/notifications", tags=["Notifications"])

@router.post("/", response_model=Notification, status_code=201)
async def create_notification(notification_data: NotificationCreate, db: Session = Depends(get_db)):
    """Créer une notification"""
    return await NotificationService.create_notification(db, notification_data)

@router.get("/user/{user_id}", response_model=List[Notification])
def get_user_notifications(user_id: str, skip: int = 0, limit: int = 50, db: Session = Depends(get_db)):
    """Récupérer les notifications d'un utilisateur"""
    notifications = db.query(NotificationDB).filter(
        NotificationDB.user_id == user_id
    ).order_by(NotificationDB.created_at.desc()).offset(skip).limit(limit).all()
    
    # Convertir manuellement les objets DB en modèles Pydantic
    result = []
    for notif in notifications:
        result.append(Notification(
            id=str(notif.id),  # Convertir l'UUID en string
            user_id=notif.user_id,
            case_id=notif.case_id,
            type=notif.type,
            title=notif.title,
            message=notif.message,
            is_read=notif.is_read,
            created_at=notif.created_at
        ))
    return result

@router.patch("/{notification_id}/read")
def mark_as_read(notification_id: str, db: Session = Depends(get_db)):
    """Marquer une notification comme lue"""
    notification = db.query(NotificationDB).filter(NotificationDB.id == notification_id).first()
    if notification:
        notification.is_read = True
        db.commit()
        return {"message": "Notification marked as read"}
    return {"message": "Notification not found"}, 404
