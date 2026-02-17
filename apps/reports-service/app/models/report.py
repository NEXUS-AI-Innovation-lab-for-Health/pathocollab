from sqlalchemy import Column, String, DateTime, Text, Boolean
from sqlalchemy.ext.declarative import declarative_base
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timezone
import uuid

Base = declarative_base()

class ReportDB(Base):
    __tablename__ = "reports"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    case_id = Column(String, nullable=False, index=True)
    user_id = Column(String, nullable=False)
    title = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    is_final = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

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

class ReportAssistRequest(BaseModel):
    case_id: str
    user_id: str
    annotations: list = []
    previous_reports: list = []
    patient_context: Optional[str] = None
    instruction: str = "Génère un rapport médical détaillé"
