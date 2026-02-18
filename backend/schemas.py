from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional
from datetime import datetime

# User schemas
class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserRegister(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    role: str = "anatomopathologiste"

class UserResponse(BaseModel):
    id: str
    email: str
    full_name: str
    role: str
    is_active: bool
    created_at: datetime
    
    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"

class TokenData(BaseModel):
    email: Optional[str] = None

# Case schemas
class CaseBase(BaseModel):
    patient_id: str
    title: str
    description: str
    status: str = "pending"
    assigned_specialists: List[str] = []

class CaseCreate(CaseBase):
    pass

class CaseResponse(CaseBase):
    id: str
    created_by: str
    created_at: datetime
    updated_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True

# Patient schemas
class PatientBase(BaseModel):
    full_name: str
    age: int
    gender: str
    medical_history: Optional[str] = None
    symptoms: Optional[str] = None
    imaging_notes: Optional[str] = None
    date_of_birth: Optional[datetime] = None

class PatientCreate(PatientBase):
    pass

class PatientResponse(PatientBase):
    id: str
    created_at: datetime
    updated_at: Optional[datetime] = None
    date_of_birth: Optional[datetime] = None
    
    class Config:
        from_attributes = True

# StatusCheck schemas
class StatusCheckBase(BaseModel):
    client_name: str

# Image schemas
class PatientImageItem(BaseModel):
    id: str                 
    object_name: str
    filename: str
    last_modified: Optional[str] = None
    size: Optional[int] = None
    url: str
    image_type: str  

class StatusCheckCreate(StatusCheckBase):
    pass

class StatusCheckResponse(StatusCheckBase):
    id: str
    timestamp: datetime
    created_at: datetime
    
    class Config:
        from_attributes = True
