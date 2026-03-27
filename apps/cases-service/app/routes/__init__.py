from .patients import router as patients_router
from .cases import router as cases_router
from .discussions import router as discussions_router

__all__ = ['patients_router', 'cases_router', 'discussions_router']
