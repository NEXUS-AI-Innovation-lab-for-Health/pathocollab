from __future__ import annotations

import enum
import uuid
from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, ConfigDict
from sqlalchemy import Boolean, DateTime, Enum as SQLEnum, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class NotificationType(str, enum.Enum):
    CASE_ASSIGNED = "case_assigned"
    TURN_READY = "turn_ready"
    CASE_COMPLETED = "case_completed"
    SPECIALIST_REQUESTED = "specialist_requested"
    COMMENT_ADDED = "comment_added"


class NotificationDB(Base):
    __tablename__ = "notifications"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    case_id: Mapped[str] = mapped_column(String, nullable=False, index=True)

    notification_type = mapped_column(
        SQLEnum(
            NotificationType,
            name="notification_type",
            create_type=False,
            values_callable=lambda enum_cls: [e.value for e in enum_cls],
        ),
        nullable=False,
    )

    title: Mapped[str] = mapped_column(String, nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )


class NotificationBase(BaseModel):
    user_id: str
    case_id: str
    type: NotificationType
    title: str
    message: str


class NotificationCreate(NotificationBase):
    pass


class Notification(NotificationBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    is_read: bool = False
    created_at: datetime


class NotificationReadResponse(BaseModel):
    success: bool
    message: str
    notification_id: str
    unread_count: int


class NotificationListResponse(BaseModel):
    items: list[Notification]
    total: Optional[int] = None
    unread_count: int = 0