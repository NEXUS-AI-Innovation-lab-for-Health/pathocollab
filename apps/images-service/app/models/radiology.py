from sqlalchemy import Column, String, DateTime, Integer, Text
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timezone
import uuid

from .base import Base


class RadiologySeriesLinkDB(Base):
    __tablename__ = "radiology_series_links"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))

    app_patient_id = Column(String, nullable=False, index=True)
    uploaded_by = Column(String, nullable=False)

    orthanc_patient_id = Column(String, nullable=False, index=True)
    orthanc_study_id = Column(String, nullable=False, index=True)
    orthanc_series_id = Column(String, nullable=False, index=True)
    preview_instance_id = Column(String, nullable=True)

    patient_name = Column(String, nullable=True)
    dicom_patient_id = Column(String, nullable=True)
    study_instance_uid = Column(String, nullable=True)
    series_instance_uid = Column(String, nullable=True)

    modality = Column(String, nullable=True)
    study_date = Column(String, nullable=True)
    study_description = Column(Text, nullable=True)
    series_description = Column(Text, nullable=True)
    instances_count = Column(Integer, nullable=False, default=0)

    raw_minio_prefix = Column(String, nullable=True)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


class RadiologySeriesSummary(BaseModel):
    id: str
    app_patient_id: str
    uploaded_by: str

    orthanc_patient_id: str
    orthanc_study_id: str
    orthanc_series_id: str
    preview_instance_id: Optional[str] = None

    patient_name: Optional[str] = None
    dicom_patient_id: Optional[str] = None
    study_instance_uid: Optional[str] = None
    series_instance_uid: Optional[str] = None

    modality: Optional[str] = None
    study_date: Optional[str] = None
    study_description: Optional[str] = None
    series_description: Optional[str] = None
    instances_count: int = 0

    raw_minio_prefix: Optional[str] = None

    class Config:
        from_attributes = True