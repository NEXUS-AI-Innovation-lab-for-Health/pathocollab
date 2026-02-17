from sqlalchemy import Column, String, DateTime, Boolean, Text, Enum as SQLEnum
from sqlalchemy.ext.declarative import declarative_base
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timezone
import uuid
import enum

Base = declarative_base()

class NotificationType(str, enum.Enum):
    CASE_ASSIGNED = "case_assigned"
    TURN_READY = "turn_ready"
    CASE_COMPLETED = "case_completed"
    SPECIALIST_REQUESTED = "specialist_requested"
    COMMENT_ADDED = "comment_added"

class NotificationDB(Base):
    __tablename__ = "notifications"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, nullable=False, index=True)
    case_id = Column(String, nullable=False, index=True)
    type = Column(SQLEnum(NotificationType), nullable=False)
    title = Column(String, nullable=False)
    message = Column(Text, nullable=False)
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    
    # Convertir l'UUID en string lors de la récupération depuis la base
    @property
    def id_str(self):
        return str(self.id) if self.id else None

class Notification(BaseModel):
    id: str
    user_id: str
    case_id: str
    type: NotificationType
    title: str
    message: str
    is_read: bool = False
    created_at: datetime
    
    class Config:
        from_attributes = True

class NotificationCreate(BaseModel):
    user_id: str
    case_id: str
    type: NotificationType
    title: str
    message: str
