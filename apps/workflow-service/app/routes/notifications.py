from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.notification import Notification, NotificationListResponse
from app.services.notification_service import NotificationService
from app.utils.database import get_db

router = APIRouter(prefix="/notifications", tags=["Notifications"])


def _to_notification_response(item) -> Notification:
    return Notification(
        id=item.id,
        user_id=item.user_id,
        case_id=item.case_id,
        type=item.notification_type,
        title=item.title,
        message=item.message,
        is_read=item.is_read,
        created_at=item.created_at,
    )


@router.get("/user/{user_id}", response_model=NotificationListResponse)
async def get_user_notifications(user_id: str, db: AsyncSession = Depends(get_db)):
    notifications = await NotificationService.list_user_notifications(db, user_id)
    unread_count = await NotificationService.count_unread_notifications(db, user_id)

    return NotificationListResponse(
        items=[_to_notification_response(item) for item in notifications],
        total=len(notifications),
        unread_count=unread_count,
    )


@router.post("/{notification_id}/read")
async def mark_notification_as_read(notification_id: str, db: AsyncSession = Depends(get_db)):
    return await NotificationService.mark_as_read(db, notification_id)