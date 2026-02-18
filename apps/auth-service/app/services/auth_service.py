from __future__ import annotations


def _role_to_str(r):
    # accepte str, Enum (UserRole), ou autre
    try:
        v = getattr(r, "value", r)
    except Exception:
        v = r
    if isinstance(v, str):
        return v.strip().lower()
    return str(v)
import uuid
from datetime import datetime, timezone
from typing import List

from fastapi import HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import UserDB, UserCreate, UserLogin, User
from app.models.token import Token
from app.utils.security import (
    create_access_token,
    create_refresh_token,
    get_password_hash,
    verify_password,
)


class AuthService:
    @staticmethod
    async def register_user(db: AsyncSession, user_data: UserCreate) -> User:
        # Vérifier si l'email existe déjà
        res = await db.execute(select(UserDB).where(UserDB.email == user_data.email))
        existing_user = res.scalars().first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered",
            )

        hashed_password = get_password_hash(user_data.password)

        db_user = UserDB(
            id=str(uuid.uuid4()),
            email=user_data.email,
            hashed_password=hashed_password,
            full_name=user_data.full_name,
            role=user_data.role,
        )
        db.add(db_user)
        await db.commit()
        await db.refresh(db_user)

        return User.model_validate(db_user)

    @staticmethod
    async def login_user(db: AsyncSession, login_data: UserLogin) -> Token:
        res = await db.execute(select(UserDB).where(UserDB.email == login_data.email))
        user = res.scalars().first()

        if not user or not verify_password(login_data.password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        if hasattr(user, "is_active") and not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is inactive",
            )

        # Mettre à jour last_login
        if hasattr(user, "last_login"):
            user.last_login = datetime.now(timezone.utc)
            await db.commit()

        role_value = getattr(user.role, "value", user.role)

        token_data = {
            "user_id": user.id,
            "email": user.email,
            "role": role_value,
        }
        access_token = create_access_token(token_data)
        refresh_token = create_refresh_token(token_data)

        return Token(access_token=access_token, refresh_token=refresh_token)

    @staticmethod
    async def get_user_by_id(db: AsyncSession, user_id: str) -> User:
        res = await db.execute(select(UserDB).where(UserDB.id == user_id))
        user = res.scalars().first()
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        return User.model_validate(user)

    @staticmethod
    async def get_user_by_email(db: AsyncSession, email: str) -> User:
        res = await db.execute(select(UserDB).where(UserDB.email == email))
        db_user = res.scalars().first()
        if not db_user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        return User.model_validate(db_user)

    @staticmethod
    async def list_users(db: AsyncSession):
        result = await db.execute(select(UserDB))  # UserDB = modèle SQLAlchemy
        return result.scalars().all()

    @staticmethod
    async def delete_user(db: AsyncSession, user_id: str) -> None:
        res = await db.execute(select(UserDB).where(UserDB.id == user_id))
        user = res.scalars().first()
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        await db.delete(user)
        await db.commit()

    @staticmethod
    async def list_specialists(db: AsyncSession) -> List[User]:
        # Même logique que ton code initial, en async
        res = await db.execute(
            select(UserDB).where(
                UserDB.is_active == True,  # noqa: E712
                UserDB.role.in_(["orthodontiste", "anatomopathologiste", "oncologue"]),
            )
        )
        specialists = res.scalars().all()
        return [User.model_validate(s) for s in specialists]

    @staticmethod
    async def count_specialists(db: AsyncSession) -> dict:
        res = await db.execute(
            select(UserDB.id).where(
                UserDB.is_active == True,  # noqa: E712
                UserDB.role.in_(["orthodontiste", "anatomopathologiste", "oncologue"]),
            )
        )
        count = len(res.scalars().all())
        return {"count": count}
