import json
from fastapi import FastAPI, APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import delete, select, text, func
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
import os
import logging
from pathlib import Path
from typing import List, Optional
from datetime import datetime, timezone, timedelta
import uuid

from database import get_db, init_db, engine
from models import User, StatusCheck, Case, Patient
from schemas import UserLogin, UserRegister, Token, CaseResponse, PatientResponse, PatientImageItem, StatusCheckResponse, CaseCreate, PatientCreate, StatusCheckCreate
from auth import verify_password, get_password_hash, create_access_token, verify_token, get_current_user

from imageAnalyse import init_image_service, mount_image_service

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# Create the main app without a prefix
app = FastAPI()

origins = [o.strip() for o in os.environ.get("CORS_ORIGINS", "").split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_credentials=False,
    allow_origins=origins if origins else ["http://10.10.69.63:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize database on startup
@app.on_event("startup")
async def startup_event():
    await init_db()
    init_image_service()

    # --- Créer les tables image-service si absentes (mode DEV) ---
    # IMPORTANT: on importe les models pour "enregistrer" leurs metadata
    from app.models.image import ImageDB
    from app.models.annotation import AnnotationDB

    # Ici, on utilise l'engine async du backend (déjà utilisé par init_db)
    from database import engine

    async with engine.begin() as conn:
        # Si vous utilisez des Base séparés, il faut cibler le bon Base.
        # Si ImageDB/AnnotationDB sont rattachés à une Base dans app/models, importez-la et utilisez-la.
        from app.models.image import Base as ImagesBase
        from app.models.annotation import Base as AnnotationsBase

        from models import Base as MainBase

        await conn.run_sync(ImagesBase.metadata.create_all)
        await conn.run_sync(AnnotationsBase.metadata.create_all)
        await conn.run_sync(MainBase.metadata.create_all)


# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Security
security = HTTPBearer()

# Add your routes to the router instead of directly to app
@api_router.get("/")
async def root():
    return {"message": "Hello World"}

@api_router.post("/auth/login", response_model=Token)
async def login(user_data: UserLogin, db: AsyncSession = Depends(get_db)):
    """Login endpoint with real authentication"""
    # Find user by email
    result = await db.execute(select(User).where(User.email == user_data.email))
    user = result.scalar_one_or_none()
    
    if not user or not verify_password(user_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou mot de passe incorrect",
            headers={"WWW-Authenticate": "Bearer"},
        ) 
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Compte désactivé"
        )
    
    access_token = create_access_token(
                        data={
                            "sub": user.email,
                            "user_id": user.id,
                            "role": user.role.value if hasattr(user.role, "value") else str(user.role),
                        }
                    )
    
    return {
        "access_token": access_token,
        "refresh_token": "demo_refresh_token",  
        "token_type": "bearer"
    }

@api_router.post("/auth/register")
async def register(user_data: UserRegister, db: AsyncSession = Depends(get_db)):
    """Register endpoint with password hashing"""
    # Check if user already exists
    result = await db.execute(select(User).where(User.email == user_data.email))
    existing_user = result.scalar_one_or_none()
    
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email déjà utilisé"
        )
    
    # Hash password
    hashed_password = get_password_hash(user_data.password)
    
    # Create new user
    new_user = User(
        email=user_data.email,
        hashed_password=hashed_password,
        full_name=user_data.full_name,
        role=user_data.role,
        is_active=True
    )
    
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    
    return {
        "id": new_user.id,
        "email": new_user.email,
        "full_name": new_user.full_name,
        "role": new_user.role,
        "is_active": new_user.is_active,
        "created_at": new_user.created_at
    }

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security), db: AsyncSession = Depends(get_db)):
    """Get current authenticated user"""
    token = credentials.credentials
    payload = verify_token(token)
    email = payload.get("sub")
    
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Utilisateur non trouvé"
        )
    
    return user

@api_router.post("/cases", response_model=CaseResponse)
async def create_case(case_data: CaseCreate, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Crée un nouveau cas clinique"""
    new_case = Case(
        patient_id=case_data.patient_id,
        title=case_data.title,
        description=case_data.description,
        status=case_data.status,
        created_by=current_user.id,
        assigned_specialists=case_data.assigned_specialists
    )
    
    db.add(new_case)
    await db.commit()
    await db.refresh(new_case)
    
    return CaseResponse(
        id=new_case.id,
        patient_id=new_case.patient_id,
        title=new_case.title,
        description=new_case.description,
        status=new_case.status,
        created_by=new_case.created_by,
        assigned_specialists=json.loads(new_case.assigned_specialists) if new_case.assigned_specialists else [],
        created_at=new_case.created_at,
        updated_at=new_case.updated_at,
        completed_at=new_case.completed_at,
    ) 

@api_router.get("/cases", response_model=List[CaseResponse])
async def get_cases(db: AsyncSession = Depends(get_db)):
    """Retourne les cas depuis la base de données"""
    result = await db.execute(select(Case))
    cases = result.scalars().all()
    return [
        CaseResponse(
            id=c.id,
            patient_id=c.patient_id,
            title=c.title,
            description=c.description,
            status=c.status,
            created_by=c.created_by,
            assigned_specialists=json.loads(c.assigned_specialists) if c.assigned_specialists else [],
            created_at=c.created_at,
            updated_at=c.updated_at,
            completed_at=c.completed_at,
        )
        for c in cases
    ]

@api_router.get("/cases/{case_id}", response_model=CaseResponse)
async def get_case(case_id: str, db: AsyncSession = Depends(get_db)):
    """Retourne un cas spécifique"""
    result = await db.execute(select(Case).where(Case.id == case_id))
    case = result.scalar_one_or_none()
    
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cas non trouvé"
        )
    
    return CaseResponse(
        id=case.id,
        patient_id=case.patient_id,
        title=case.title,
        description=case.description,
        status=case.status,
        created_by=case.created_by,
        assigned_specialists=json.loads(case.assigned_specialists) if case.assigned_specialists else [],
        created_at=case.created_at,
        updated_at=case.updated_at,
        completed_at=case.completed_at,
    )


@api_router.delete("/debug/cases")
async def debug_clear_cases(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    DEBUG ONLY: supprime tous les cas.
    Protégé par token + flag d'environnement.
    """
    # Sécurité: activable uniquement si explicitement autorisé
    if os.getenv("ENABLE_DEBUG_ENDPOINTS", "false").lower() != "true":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")

    # Optionnel: restreindre à certains rôles
    # (adapte selon tes valeurs réelles de role)
    if getattr(current_user, "role", "").lower() not in {"admin", "enseignant"}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

    # Compter avant suppression
    count_res = await db.execute(select(func.count()).select_from(Case))
    total = count_res.scalar_one()

    # Supprimer
    await db.execute(delete(Case))
    await db.commit()

    return {"deleted_cases": total}



@api_router.get("/patients", response_model=List[PatientResponse])
async def list_patients(
    current_user: User = Depends(get_current_user),  
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Patient))
    patients = result.scalars().all()
    return patients


@api_router.get("/patients/{patient_id}", response_model=PatientResponse)
async def get_patient(patient_id: str, db: AsyncSession = Depends(get_db)):
    """Retourne les informations d'un patient"""
    result = await db.execute(select(Patient).where(Patient.id == patient_id))
    patient = result.scalar_one_or_none()
    
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient non trouvé"
        )
    
    return PatientResponse(
        id=patient.id,
        full_name=patient.full_name,
        age=patient.age,
        gender=patient.gender,
        medical_history=patient.medical_history,
        symptoms=patient.symptoms,
        imaging_notes=patient.imaging_notes,
        created_at=patient.created_at
    )


@api_router.post("/patients/create", response_model=PatientResponse)
async def create_patient(patient_data: PatientCreate, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Crée un nouveau patient"""
    new_patient = Patient(
        full_name=patient_data.full_name,
        age=patient_data.age,
        gender=patient_data.gender,
        medical_history=patient_data.medical_history,
        symptoms=patient_data.symptoms,
        imaging_notes=patient_data.imaging_notes
    )
    
    db.add(new_patient)
    await db.commit()
    await db.refresh(new_patient)
    
    return new_patient


@api_router.get("/patients/{patient_id}/images")
async def list_patient_objects(patient_id: str):
    """Retourne les images d'un patient"""

    from app.services.minio_service import MinioService

    minio_service = MinioService()

    prefix = f"patients/{patient_id}/"

    objects = minio_service.list_objects(prefix=prefix)  
    out = []

    for o in objects:
        name = o["object_name"]
        # ignore placeholder
        if name.endswith("/.keep"):
            continue
        out.append({
            "object_name": name,
            "filename": name.split("/")[-1],
            "size": o.get("size"),
            "last_modified": o.get("last_modified"),
            "url": minio_service.get_presigned_url(name),
            "category": "dzi" if "/dzi/" in name else ("raw" if "/raw/" in name else "other")
        })
    return out

@api_router.get("/patients/{patient_id}", response_model=PatientResponse)
async def get_patient(patient_id: str, db: AsyncSession = Depends(get_db)):
    """Retourne les informations d'un patient"""
    result = await db.execute(select(Patient).where(Patient.id == patient_id))
    patient = result.scalar_one_or_none()
    
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient non trouvé"
        )
    
    return patient

@api_router.post("/status", response_model=StatusCheckResponse)
async def create_status_check(input: StatusCheckCreate, db: AsyncSession = Depends(get_db)):
    status_check = StatusCheck(
        client_name=input.client_name,
        timestamp=datetime.now(timezone.utc)
    )
    
    db.add(status_check)
    await db.commit()
    await db.refresh(status_check)
    
    return status_check

@api_router.get("/status", response_model=List[StatusCheckResponse])
async def get_status_checks(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(StatusCheck))
    status_checks = result.scalars().all()
    return status_checks

mount_image_service(api_router, app)

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_event():
    await engine.dispose()