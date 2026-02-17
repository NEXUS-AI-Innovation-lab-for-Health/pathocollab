from sqlalchemy import Column, String, DateTime, Text, Enum as SQLEnum, Float
from sqlalchemy.ext.declarative import declarative_base
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timezone
import uuid
import enum

Base = declarative_base()

class AnnotationType(str, enum.Enum):
    MANUAL = "manual"
    AI_DETECTED = "ai_detected"
    AI_ASSISTED = "ai_assisted"

class AnnotationDB(Base):
    __tablename__ = "annotations"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    image_id = Column(String, nullable=False, index=True)
    case_id = Column(String, nullable=False, index=True)
    user_id = Column(String, nullable=False)
    type = Column(SQLEnum(AnnotationType), default=AnnotationType.MANUAL)
    coordinates = Column(Text, nullable=False)  # JSON
    label = Column(String, nullable=False)
    confidence = Column(Float, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

class Annotation(BaseModel):
    id: str
    image_id: str
    case_id: str
    user_id: str
    type: AnnotationType
    coordinates: dict
    label: str
    confidence: Optional[float] = None
    notes: Optional[str] = None
    created_at: datetime
    
    class Config:
        from_attributes = True

class AnnotationCreate(BaseModel):
    image_id: str
    case_id: str
    type: AnnotationType = AnnotationType.MANUAL
    coordinates: dict
    label: str
    confidence: Optional[float] = None
    notes: Optional[str] = None
