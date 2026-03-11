from sqlalchemy import Column, String, DateTime, Text, Enum as SQLEnum
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
import uuid
import enum

from .base import Base


class AnnotationType(str, enum.Enum):
    MANUAL = "manual"
    AI_DETECTED = "ai_detected"
    AI_ASSISTED = "ai_assisted"


class AnnotationDB(Base):
    __tablename__ = "annotations"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    image_id = Column(String, nullable=False, index=True)
    case_id = Column(String, nullable=False, index=True)

    user_id = Column(String, nullable=False, index=True)
    owner_name = Column(String, nullable=True)

    type = Column(
        SQLEnum(AnnotationType, name="annotationtype"),
        default=AnnotationType.MANUAL,
        nullable=False,
    )

    coordinates = Column(Text, nullable=False)  # JSON string

    label = Column(String, nullable=False)
    severity = Column(String, nullable=True)
    category = Column(String, nullable=True)
    description = Column(Text, nullable=True)
    recommendation = Column(Text, nullable=True)
    tags = Column(Text, nullable=True)  # JSON string

    stroke_color = Column(String, nullable=True)
    fill_color = Column(String, nullable=True)
    stroke_width = Column(String, nullable=True)

    confidence = Column(String, nullable=True)
    notes = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


class Annotation(BaseModel):
    id: str
    image_id: str
    case_id: str
    user_id: str
    owner_name: Optional[str] = None
    type: AnnotationType
    coordinates: Dict[str, Any]
    label: str
    severity: Optional[str] = None
    category: Optional[str] = None
    description: Optional[str] = None
    recommendation: Optional[str] = None
    tags: List[str] = []
    stroke_color: Optional[str] = None
    fill_color: Optional[str] = None
    stroke_width: Optional[float] = None
    confidence: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class AnnotationCreate(BaseModel):
    image_id: str
    case_id: str
    type: AnnotationType = AnnotationType.MANUAL
    coordinates: Dict[str, Any]
    label: str
    severity: Optional[str] = None
    category: Optional[str] = None
    description: Optional[str] = None
    recommendation: Optional[str] = None
    tags: List[str] = []
    stroke_color: Optional[str] = None
    fill_color: Optional[str] = None
    stroke_width: Optional[float] = None
    confidence: Optional[str] = None
    notes: Optional[str] = None