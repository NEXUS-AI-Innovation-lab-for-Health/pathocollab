from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class ImageBase(BaseModel):
    filename: str
    original_filename: str
    content_type: str
    size: int

class ImageCreate(ImageBase):
    case_id: Optional[int] = None
    object_name: str
    url: str

class Image(ImageBase):
    id: int
    object_name: str
    case_id: Optional[int] = None
    url: str
    uploaded_at: datetime
    
    class Config:
        from_attributes = True
