from sqlalchemy import Column, String, Boolean, DateTime, Enum as SQLEnum
import sqlalchemy
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime, timezone
from pydantic import BaseModel, ConfigDict, EmailStr, Field
from typing import Optional
import enum
from enum import Enum
import uuid

Base = declarative_base()

class UserRole(str, enum.Enum):
    ADMIN = "admin"
    ANATOMOPATHOLOGISTE = "anatomopathologiste"
    ONCOLOGUE = "oncologue"
    RADIOLOGUE = "radiologue"
    MEDECIN_GENERALISTE = "medecin_generaliste"

class UserDB(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    email: Mapped[str] = mapped_column(String, unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String, nullable=False)
    full_name: Mapped[str] = mapped_column(String, nullable=False)

    role: Mapped[UserRole] = mapped_column(
        SQLEnum(
            UserRole,
            name="userrole",
            values_callable=lambda enum_cls: [e.value for e in enum_cls]
        ),
        nullable=False
    )

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    last_login: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

class User(BaseModel):
    id: str
    email: EmailStr
    full_name: str
    role: str
    is_active: bool = True
    is_verified: bool = False
    created_at: datetime
    last_login: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    email: str
    full_name: Optional[str] = None
    role: UserRole


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)
    full_name: str = Field(..., min_length=2)
    role: UserRole = UserRole.ANATOMOPATHOLOGISTE

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    is_active: Optional[bool] = None
