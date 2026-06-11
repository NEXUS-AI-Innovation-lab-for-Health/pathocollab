from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes import patients, cases, discussions
import os
from dotenv import load_dotenv
import logging

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="PathoCollab Cases Service",
    description="Gestion des cas patients et dossiers cliniques",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(patients.router, prefix="/api")
app.include_router(cases.router, prefix="/api")
app.include_router(discussions.router, prefix="/api")

@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "cases-service"}

@app.get("/metrics")
def metrics():
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("SERVICE_PORT", "8002"))
    uvicorn.run("app.main:app", host="0.0.0.0", port=port, reload=True)