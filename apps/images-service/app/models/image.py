from sqlalchemy import Column, String, DateTime, Integer, Boolean, Text
from sqlalchemy.ext.declarative import declarative_base
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timezone
import uuid

from .base import Base

class ImageDB(Base):
    __tablename__ = "images"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    case_id = Column(String, nullable=False, index=True)
    filename = Column(String, nullable=False)
    minio_path = Column(String, nullable=False, unique=True)
    mime_type = Column(String, nullable=False)
    file_size = Column(Integer, nullable=False)
    width = Column(Integer, nullable=True)
    height = Column(Integer, nullable=True)
    uploaded_by = Column(String, nullable=False)
    is_encrypted = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

class Image(BaseModel):
    id: str
    case_id: str
    filename: str
    minio_path: str
    mime_type: str
    file_size: int
    width: Optional[int] = None
    height: Optional[int] = None
    uploaded_by: str
    is_encrypted: bool = True
    created_at: datetime
    
    class Config:
        from_attributes = True

class ImageUploadResponse(BaseModel):
    image_id: str
    filename: str
    url: str
    message: str = "Image uploaded successfully"
