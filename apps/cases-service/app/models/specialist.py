from sqlalchemy import Column, String, Integer, DateTime, Boolean
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from .base import Base

class SpecialistDB(Base):
    __tablename__ = "specialists"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    specialty = Column(String(255), nullable=False)
    phone = Column(String(50), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class Specialist(BaseModel):
    id: int
    name: str
    email: str
    specialty: str
    phone: Optional[str] = None
    is_active: bool
    created_at: datetime
    
    class Config:
        from_attributes = True

class SpecialistCreate(BaseModel):
    name: str
    email: str
    specialty: str
    phone: Optional[str] = None
