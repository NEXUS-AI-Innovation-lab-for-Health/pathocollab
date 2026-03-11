from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel
from sqlalchemy import Boolean, Column, DateTime, String, Text

from .base import Base


class ReportDB(Base):
    __tablename__ = "reports"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    case_id = Column(String, nullable=False, index=True)
    user_id = Column(String, nullable=False)
    title = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    is_final = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


class Report(BaseModel):
    id: str
    case_id: str
    user_id: str
    title: str
    content: str
    is_final: bool = False
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ReportCreate(BaseModel):
    case_id: str
    user_id: str
    title: str
    content: str
    is_final: bool = False


class ReportUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    is_final: Optional[bool] = None


class ReportAssistRequest(BaseModel):
    report_id: str
    case_id: Optional[str] = None
    user_id: Optional[str] = None
    annotations: list = []
    previous_reports: list = []
    patient_context: Optional[str] = None
    instruction: str = "Génère un rapport médical détaillé"