# app/main.py
from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from app.routes import images, annotations, wsi, radiology
from app.utils.database import get_db
from app.models.base import Base
from app.models.image import ImageDB
from app.models.annotation import AnnotationDB
from app.models.radiology import RadiologySeriesLinkDB
from app.utils.database import engine
import os
from dotenv import load_dotenv
import logging
import base64
import json
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi import Request

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="PathoCollab Images Service",
    description="Gestion des images WSI et annotations",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://10.10.69.63:3000",
        "http://192.168.1.21:3000"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    logger.error("Validation error on %s %s", request.method, request.url.path)
    logger.error("Validation details: %s", exc.errors())
    try:
        body = await request.body()
        logger.error("Request body: %s", body.decode("utf-8", errors="ignore"))
    except Exception:
        logger.error("Unable to read request body")
    return JSONResponse(
        status_code=422,
        content={"detail": exc.errors()},
    )

def get_current_user_from_bearer(authorization: str = Header(default=None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")

    token = authorization.split(" ", 1)[1]
    try:
        payload_part = token.split(".")[1]
        padding = "=" * (-len(payload_part) % 4)
        payload = json.loads(base64.urlsafe_b64decode(payload_part + padding).decode("utf-8"))

        user_id = payload.get("sub") or payload.get("email")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token payload")

        return type("CurrentUser", (), {
            "id": user_id,
            "email": payload.get("email"),
            "sub": payload.get("sub"),
            "name": payload.get("name"),
            "full_name": payload.get("name"),
        })()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Invalid bearer token: {str(e)}")

app.dependency_overrides[images.get_db_override] = get_db
app.dependency_overrides[radiology.get_db_override] = get_db
app.dependency_overrides[annotations.get_db_override] = get_db
app.dependency_overrides[annotations.get_current_user_override] = get_current_user_from_bearer

@app.on_event("startup")
async def startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables checked/created")

app.include_router(images.router, prefix="/api")
app.include_router(annotations.router, prefix="/api")
app.include_router(wsi.router, prefix="/api")
app.include_router(radiology.router, prefix="/api")

@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "images-service"}

@app.get("/metrics")
def metrics():
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("SERVICE_PORT", "8004"))
    uvicorn.run("app.main:app", host="0.0.0.0", port=port, reload=True)