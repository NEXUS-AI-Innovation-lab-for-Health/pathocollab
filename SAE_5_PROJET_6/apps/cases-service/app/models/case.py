from sqlalchemy import Column, String, DateTime, Text, Enum as SQLEnum
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime, timezone
import uuid
import enum
from .base import Base

class CaseStatus(str, enum.Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

class CaseDB(Base):
    __tablename__ = "cases"
    
    id = Column(String, primary_key=True, default=lambda: f"BIO-2025-{str(uuid.uuid4().int)[:6]}")
    patient_id = Column(String, nullable=False, index=True)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    status = Column(SQLEnum(CaseStatus), default=CaseStatus.PENDING)
    created_by = Column(String, nullable=False)
    assigned_specialists = Column(Text, nullable=True)  # JSON string
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    completed_at = Column(DateTime(timezone=True), nullable=True)

class Case(BaseModel):
    id: str
    patient_id: str
    title: str
    description: Optional[str] = None
    status: CaseStatus
    created_by: str
    assigned_specialists: Optional[List[str]] = []
    created_at: datetime
    completed_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True

class CaseCreate(BaseModel):
    patient_id: str
    title: str = Field(..., min_length=5)
    description: Optional[str] = None
    created_by: str
    assigned_specialists: List[str] = []
