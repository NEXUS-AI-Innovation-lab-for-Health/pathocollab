from sqlalchemy import Column, Date, String, Integer, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from pydantic import BaseModel, Field
from typing import Optional
from datetime import date, datetime, timezone
import uuid

Base = declarative_base()

class PatientDB(Base):
    __tablename__ = "patients"
    
    id = Column(String, primary_key=True, default=lambda: f"PAT-{str(uuid.uuid4())[:8]}")
    full_name = Column(String, nullable=False)
    age = Column(Integer, nullable=False)
    gender = Column(String, nullable=False)
    date_of_birth = Column(Date, nullable=True)
    medical_history = Column(Text, nullable=True)
    symptoms = Column(Text, nullable=True)
    imaging_notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

class Patient(BaseModel):
    id: str
    full_name: str
    age: int
    gender: str
    medical_history: Optional[str] = None
    symptoms: Optional[str] = None
    imaging_notes: Optional[str] = None
    created_at: datetime
    date_of_birth: Optional[date] = None
    
    class Config:
        from_attributes = True

class PatientCreate(BaseModel):
    full_name: str = Field(..., min_length=2)
    age: int = Field(..., ge=0, le=150)
    gender: str = Field(..., pattern="^(Homme|Femme|Autre)$")
    medical_history: Optional[str] = None
    symptoms: Optional[str] = None
    imaging_notes: Optional[str] = None
    date_of_birth: Optional[date] = None
