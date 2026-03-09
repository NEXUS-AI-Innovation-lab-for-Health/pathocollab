from typing import Any, Dict, List, Optional
from pydantic import BaseModel


class OlgaField(BaseModel):
    field_hint: Optional[str] = ""
    field_required: bool = False
    unique_id: str
    field_key: str
    field_events: Optional[Dict[str, Any]] = {}
    field_mode: Optional[str] = "edit"
    field_label: Optional[str] = ""
    field_type: str


class OlgaFormSchema(BaseModel):
    form_version: str
    models: List[str]
    form_label: str
    last_updated: str
    form: List[OlgaField]
    form_category: str
    form_id: str


class DynamicFormSubmission(BaseModel):
    form_id: str
    data: Dict[str, Any]