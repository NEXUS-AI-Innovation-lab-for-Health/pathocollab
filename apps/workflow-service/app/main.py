from __future__ import annotations

import logging
import os

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes import notifications, workflow

load_dotenv()

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

app = FastAPI(
    title="Pixtral Workflow Service",
    description="Gestion des workflows collaboratifs et notifications, avec mode local et mode Olga.",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000", "http://10.10.69.63:3000", "http://192.168.1.21:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(workflow.router, prefix="/api")
app.include_router(notifications.router, prefix="/api")


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "healthy", "service": "workflow-service"}


@app.get("/metrics")
def metrics() -> dict[str, str]:
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("SERVICE_PORT", "8003"))
    uvicorn.run("app.main:app", host="0.0.0.0", port=port, reload=True)
