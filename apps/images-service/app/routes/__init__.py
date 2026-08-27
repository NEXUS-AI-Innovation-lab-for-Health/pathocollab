from .annotations import router as annotations_router
from .radiology import router as radiology_router
from .wsi import router as wsi_router

__all__ = [
    "annotations_router",
    "radiology_router",
    "wsi_router",
]
