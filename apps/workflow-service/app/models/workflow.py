from __future__ import annotations

import enum
import json
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from sqlalchemy import Boolean, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class WorkflowEngine(str, enum.Enum):
    LOCAL = "local"
    OLGA = "olga"


class WorkflowDB(Base):
    __tablename__ = "workflows"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    case_id: Mapped[str] = mapped_column(String, nullable=False, index=True, unique=True)
    specialists_order: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    current_step: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    workflow_engine: Mapped[str] = mapped_column(String, nullable=False, default=WorkflowEngine.LOCAL.value)
    olga_workflow_code: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    olga_session_id: Mapped[Optional[str]] = mapped_column(String, nullable=True, index=True)
    olga_status: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    is_completed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    def specialists_as_list(self) -> list[str]:
        if not self.specialists_order:
            return []
        try:
            value = json.loads(self.specialists_order)
            return value if isinstance(value, list) else []
        except json.JSONDecodeError:
            return []


class WorkflowBase(BaseModel):
    case_id: str
    specialists_order: list[str] = Field(default_factory=list)
    workflow_engine: WorkflowEngine = WorkflowEngine.LOCAL
    olga_workflow_code: Optional[str] = None

    @field_validator("specialists_order", mode="before")
    @classmethod
    def parse_specialists_order(cls, value: Any) -> list[str]:
        if value is None:
            return []
        if isinstance(value, list):
            return [str(item).strip() for item in value if str(item).strip()]
        if isinstance(value, str):
            raw = value.strip()
            if not raw:
                return []
            try:
                parsed = json.loads(raw)
                if isinstance(parsed, list):
                    return [str(item).strip() for item in parsed if str(item).strip()]
            except json.JSONDecodeError:
                pass
            return [item.strip() for item in raw.split(",") if item.strip()]
        raise ValueError("specialists_order doit être une liste ou une chaîne JSON valide")


class WorkflowCreate(WorkflowBase):
    @model_validator(mode="after")
    def validate_mode(self) -> "WorkflowCreate":
        if self.workflow_engine == WorkflowEngine.LOCAL and not self.specialists_order:
            raise ValueError("specialists_order est obligatoire pour un workflow local")
        if self.workflow_engine == WorkflowEngine.OLGA and not self.olga_workflow_code:
            raise ValueError("olga_workflow_code est obligatoire pour un workflow Olga")
        return self


class WorkflowUpdate(BaseModel):
    specialists_order: Optional[list[str]] = None
    current_step: Optional[int] = None
    is_completed: Optional[bool] = None
    olga_status: Optional[str] = None


class Workflow(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    case_id: str
    specialists_order: list[str] = Field(default_factory=list)
    current_step: int = 0
    workflow_engine: WorkflowEngine = WorkflowEngine.LOCAL
    olga_workflow_code: Optional[str] = None
    olga_session_id: Optional[str] = None
    olga_status: Optional[str] = None
    is_completed: bool = False
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime] = None

    @model_validator(mode="before")
    @classmethod
    def normalize_from_orm(cls, value: Any) -> Any:
        if isinstance(value, WorkflowDB):
            return {
                "id": value.id,
                "case_id": value.case_id,
                "specialists_order": value.specialists_as_list(),
                "current_step": value.current_step,
                "workflow_engine": value.workflow_engine,
                "olga_workflow_code": value.olga_workflow_code,
                "olga_session_id": value.olga_session_id,
                "olga_status": value.olga_status,
                "is_completed": value.is_completed,
                "created_at": value.created_at,
                "updated_at": value.updated_at,
                "completed_at": value.completed_at,
            }
        return value


class OlgaTaskCompleteRequest(BaseModel):
    data: dict[str, Any] = Field(default_factory=dict)


class OlgaTasksResponse(BaseModel):
    workflow_id: str
    session_id: str
    tasks: list[dict[str, Any]]
