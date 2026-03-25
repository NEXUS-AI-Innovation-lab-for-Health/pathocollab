from sqlalchemy import Column, String, DateTime, Text, Enum as SQLEnum, Float
from pydantic import BaseModel, Field
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

    # type métier / provenance, pas la forme graphique
    type = Column(
        SQLEnum(
            AnnotationType,
            name="annotationtype",
            values_callable=lambda enum_cls: [e.value for e in enum_cls],
            validate_strings=True,
        ),
        default=AnnotationType.MANUAL.value,
        nullable=False,
    )

    coordinates = Column(Text, nullable=False)

    label = Column(String, nullable=False)
    severity = Column(String, nullable=True)
    category = Column(String, nullable=True)
    description = Column(Text, nullable=True)
    recommendation = Column(Text, nullable=True)
    tags = Column(Text, nullable=True)

    stroke_color = Column(String, nullable=True)
    fill_color = Column(String, nullable=True)
    stroke_width = Column(String, nullable=True)

    confidence = Column(Float, nullable=True)
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

    # réponse souple côté API
    type: str = "manual"

    coordinates: Dict[str, Any]
    label: str
    severity: Optional[str] = None
    category: Optional[str] = None
    description: Optional[str] = None
    recommendation: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    stroke_color: Optional[str] = None
    fill_color: Optional[str] = None
    stroke_width: Optional[float] = None
    confidence: Optional[float] = None
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class AnnotationCreate(BaseModel):
    image_id: str
    case_id: str

    # on accepte n'importe quelle string entrante pour éviter le 422
    # la route forcera ensuite la vraie valeur métier
    type: Optional[str] = "manual"

    coordinates: Dict[str, Any]
    label: str
    severity: Optional[str] = None
    category: Optional[str] = None
    description: Optional[str] = None
    recommendation: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    stroke_color: Optional[str] = None
    fill_color: Optional[str] = None
    stroke_width: Optional[float] = None
    confidence: Optional[float] = None
    notes: Optional[str] = None