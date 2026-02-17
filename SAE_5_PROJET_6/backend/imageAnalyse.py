import sys
import logging
from pathlib import Path
from fastapi import APIRouter

from database import get_db

logger = logging.getLogger(__name__)

def _add_images_service_to_path():
    backend_dir = Path(__file__).resolve().parent           # backend/
    project_root = backend_dir.parent                       # racine projet
    images_service_root = project_root / "apps" / "images-service"

    if not images_service_root.exists():
        raise RuntimeError(f"images-service not found: {images_service_root}")

    # On ajoute le dossier qui contient le package "app"
    if str(images_service_root) not in sys.path:
        sys.path.insert(0, str(images_service_root))
        logger.info(f"Added to sys.path: {images_service_root}")

def init_image_service():
    """Crée le bucket MinIO au startup."""
    _add_images_service_to_path()
    from app.services.minio_service import MinioService
    MinioService()
    logger.info("Image-service initialized (MinIO bucket ensured).")

def mount_image_service(api_router: APIRouter, app):
    """Monte /api/images et /api/annotations dans le router principal."""
    _add_images_service_to_path()
    from app.routes.images import router as images_router, get_db_override as images_db_override
    from app.routes.annotations import router as annotations_router, get_db_override as ann_db_override, get_current_user_override as ann_current_user_override
    from app.routes.debug_browser import router as debug_router
    from app.routes.wsi import router as wsi_router
    from app.routes.debug_wsi_dzi import router as wsi_dzi_debug_router
    from database import get_db
    from auth import get_current_user

    app.dependency_overrides[images_db_override] = get_db
    app.dependency_overrides[ann_db_override] = get_db
    app.dependency_overrides[ann_current_user_override] = get_current_user

    api_router.include_router(images_router)        # le router a déjà prefix="/images"
    api_router.include_router(annotations_router)   # idem prefix="/annotations"
    api_router.include_router(debug_router)         # prefix="/debug"
    api_router.include_router(wsi_router)           # prefix="/wsi"
    api_router.include_router(wsi_dzi_debug_router) # prefix="/debug/wsi-dzi"
    logger.info("Image-service routers mounted.")
