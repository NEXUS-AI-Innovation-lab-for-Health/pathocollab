from sqlalchemy import Column, String, DateTime, Text, ForeignKey
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime, timezone
import uuid

from .base import Base


class DiscussionMessageDB(Base):
    __tablename__ = "discussion_messages"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    case_id = Column(String, ForeignKey("cases.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(String, nullable=False, index=True)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


class DiscussionMessage(BaseModel):
    id: str
    case_id: str
    user_id: str
    content: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class DiscussionMessageCreate(BaseModel):
    content: str = Field(..., min_length=1, max_length=5000)


class DiscussionMessageUpdate(BaseModel):
    content: str = Field(..., min_length=1, max_length=5000)