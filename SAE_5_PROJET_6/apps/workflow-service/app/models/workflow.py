from sqlalchemy import Column, String, DateTime, Integer, Text, Boolean
from sqlalchemy.ext.declarative import declarative_base
from pydantic import BaseModel, validator, Field
from typing import Optional, List, Union
from datetime import datetime, timezone
import uuid
import json

Base = declarative_base()

class WorkflowDB(Base):
    __tablename__ = "workflows"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    case_id = Column(String, nullable=False, index=True)
    specialists_order = Column(Text, nullable=False)  # Stocké sous forme de chaîne JSON
    current_step = Column(Integer, default=0)
    is_completed = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    completed_at = Column(DateTime(timezone=True), nullable=True)

    def to_dict(self):
        return {
            'id': self.id,
            'case_id': self.case_id,
            'specialists_order': json.loads(self.specialists_order) if self.specialists_order else [],
            'current_step': self.current_step,
            'is_completed': self.is_completed,
            'created_at': self.created_at,
            'completed_at': self.completed_at
        }

class WorkflowBase(BaseModel):
    case_id: str
    specialists_order: List[str]
    
    @validator('specialists_order', pre=True)
    def parse_specialists_order(cls, v):
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                return v.split(',')
        return v

class WorkflowCreate(WorkflowBase):
    pass

class Workflow(WorkflowBase):
    id: str
    current_step: int = 0
    is_completed: bool = False
    created_at: datetime
    updated_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }
        
    @classmethod
    def from_orm(cls, obj):
        if hasattr(obj, 'to_dict'):
            return cls(**obj.to_dict())
        return super().from_orm(obj)
