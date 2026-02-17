from fastapi import APIRouter, Depends, HTTPException, logger, status
from sqlalchemy.orm import Session
from app.models.user import UserCreate, UserLogin, User
from app.models.token import Token
from app.services.auth_service import AuthService
from app.utils.database import get_db
from typing import List

import logging
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/register", response_model=User, status_code=status.HTTP_201_CREATED)
def register(user_data: UserCreate, db: Session = Depends(get_db)):
    """Créer un nouveau compte utilisateur"""
    return AuthService.register_user(db, user_data)

@router.post("/login", response_model=Token)
def login(login_data: UserLogin, db: Session = Depends(get_db)):
    """Authentification et génération de tokens"""
    return AuthService.login_user(db, login_data)

@router.get("/me", response_model=User)
def get_current_user(user_id: str, db: Session = Depends(get_db)):
    """Récupérer le profil de l'utilisateur connecté"""
    return AuthService.get_user_by_id(db, user_id)

@router.get("/users/{user_id}", response_model=User)
def get_user(user_id: str, db: Session = Depends(get_db)):
    """Récupérer un utilisateur par ID"""
    return AuthService.get_user_by_id(db, user_id)

@router.get("/users/email/{email}", response_model=User)
def get_user_by_email(email: str, db: Session = Depends(get_db)):
    """Récupérer un utilisateur par email"""
    return AuthService.get_user_by_email(db, email)

@router.get("/specialists/count")
def count_specialists(db: Session = Depends(get_db)):
    """Compter le nombre total de spécialistes (anatomopathologistes et oncologues)"""
    try:
        return AuthService.count_specialists(db)
    except Exception as e:
        logger.exception("count_specialists failed")
        raise HTTPException(status_code=500, detail=str(e))
