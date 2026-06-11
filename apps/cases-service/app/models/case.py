from sqlalchemy import Column, String, DateTime, Text, Enum as SQLEnum, JSON
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
import uuid
import enum
from .base import Base

class CaseStatus(str, enum.Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    CLOSED = "closed"

class CaseDB(Base):
    __tablename__ = "cases"
    
    id = Column(String, primary_key=True, default=lambda: f"BIO-2026-{str(uuid.uuid4().int)[:6]}")
    patient_id = Column(String, nullable=False, index=True)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    
    status = Column(
        SQLEnum(
            CaseStatus,
            name="casestatus",
            values_callable=lambda enum_cls: [e.value for e in enum_cls]
        ),
        default=CaseStatus.PENDING,
        nullable=False
    )

    created_by = Column(String, nullable=False)
    assigned_specialists = Column(JSON, nullable=True)
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


class ExternalPatientForm(BaseModel):
    id: Optional[str] = None
    external_patient_id: Optional[str] = None
    full_name: Optional[str] = None
    age: Optional[int] = None
    gender: Optional[str] = None
    date_of_birth: Optional[str] = None
    medical_history: Optional[str] = ""
    symptoms: Optional[str] = ""
    imaging_notes: Optional[str] = ""


class ExternalCaseInfo(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = ""


class ExternalWorkflowInfo(BaseModel):
    specialists_order: List[str] = Field(default_factory=list)


class ExternalCaseCreate(BaseModel):
    source: Optional[str] = "external"
    external_reference: Optional[str] = None

    case: Optional[ExternalCaseInfo] = None
    patient: Optional[ExternalPatientForm] = None
    patient_form: Optional[Dict[str, Any]] = None

    workflow: Optional[ExternalWorkflowInfo] = None
    specialists_order: Optional[List[str]] = None

    metadata: Dict[str, Any] = Field(default_factory=dict)