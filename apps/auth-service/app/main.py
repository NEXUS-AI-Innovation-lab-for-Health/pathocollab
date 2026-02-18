from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes import auth
import os
from dotenv import load_dotenv
import logging

load_dotenv()

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Pixtral Auth Service",
    description="Service d'authentification pour la plateforme Pixtral",
    version="1.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000", "http://10.10.69.63:3000", "http://192.168.1.21:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routes
app.include_router(auth.router, prefix="/api")

@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "auth-service"}

@app.get("/metrics")
def metrics():
    # TODO: Implémenter les métriques Prometheus
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("SERVICE_PORT", "8001"))
    uvicorn.run("app.main:app", host="0.0.0.0", port=port, reload=True)
