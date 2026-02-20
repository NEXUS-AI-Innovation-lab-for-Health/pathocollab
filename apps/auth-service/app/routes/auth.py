from __future__ import annotations

import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps.auth import get_current_user
from app.models.user import UserCreate, UserLogin, User, UserDB, UserOut
from app.models.token import Token
from app.services.auth_service import AuthService
from app.utils.database import get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=User, status_code=status.HTTP_201_CREATED)
async def register(user_data: UserCreate, db: AsyncSession = Depends(get_db)):
    """Créer un nouveau compte utilisateur"""
    return await AuthService.register_user(db, user_data)


@router.post("/login", response_model=Token)
async def login(login_data: UserLogin, db: AsyncSession = Depends(get_db)):
    """Authentification et génération de tokens"""
    return await AuthService.login_user(db, login_data)


@router.get("/me", response_model=User)
async def me(current_user: UserDB = Depends(get_current_user)):
    """Récupérer le profil de l'utilisateur connecté via JWT"""
    return User.model_validate(current_user)


@router.get("/users/list", response_model=List[UserOut])
async def list_users(db: AsyncSession = Depends(get_db), _: UserDB = Depends(get_current_user),) -> List[UserOut]:
    users = await AuthService.list_users(db)
    return [UserOut.model_validate(u) for u in users]


@router.get("/users/{user_id}", response_model=User)
async def get_user(user_id: str, db: AsyncSession = Depends(get_db)):
    """Récupérer un utilisateur par ID"""
    return await AuthService.get_user_by_id(db, user_id)


@router.delete("/users/{user_id}")
async def delete_user(user_id: str, db: AsyncSession = Depends(get_db)):
    """Supprimer un utilisateur par ID"""
    try:
        await AuthService.delete_user(db, user_id)
        return {"detail": "User deleted"}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("delete_user failed")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/users/email/{email}", response_model=User)
async def get_user_by_email(email: str, db: AsyncSession = Depends(get_db)):
    """Récupérer un utilisateur par email"""
    return await AuthService.get_user_by_email(db, email)


@router.get("/specialists", response_model=List[User])
async def list_specialists(db: AsyncSession = Depends(get_db)) -> List[User]:
    """Lister tous les spécialistes (anatomopathologistes et oncologues)"""
    return await AuthService.list_specialists(db)


@router.get("/specialists/count")
async def count_specialists(db: AsyncSession = Depends(get_db)):
    """Compter le nombre total de spécialistes (anatomopathologistes et oncologues)"""
    try:
        return await AuthService.count_specialists(db)
    except Exception as e:
        logger.exception("count_specialists failed")
        raise HTTPException(status_code=500, detail=str(e))
