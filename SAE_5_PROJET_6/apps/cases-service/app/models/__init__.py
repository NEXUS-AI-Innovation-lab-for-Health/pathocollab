from .base import Base
from .case import CaseDB, Case, CaseCreate, CaseStatus
from .patient import PatientDB, Patient, PatientCreate
from .specialist import SpecialistDB, Specialist, SpecialistCreate

# Exporter tous les modèles pour qu'ils soient disponibles
__all__ = [
    'Base',
    'CaseDB', 'Case', 'CaseCreate', 'CaseStatus',
    'PatientDB', 'Patient', 'PatientCreate',
    'SpecialistDB', 'Specialist', 'SpecialistCreate'
]
