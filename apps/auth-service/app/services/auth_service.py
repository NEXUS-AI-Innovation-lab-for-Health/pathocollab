from sqlalchemy.orm import Session
from app.models.user import UserDB, UserCreate, UserLogin, User
from app.models.token import Token
from app.utils.security import (
    verify_password,
    get_password_hash,
    create_access_token,
    create_refresh_token
)
from fastapi import HTTPException, status
from datetime import datetime, timezone
import uuid

class AuthService:
    @staticmethod
    def register_user(db: Session, user_data: UserCreate) -> User:
        # Vérifier si l'email existe déjà
        existing_user = db.query(UserDB).filter(UserDB.email == user_data.email).first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        
        # Créer l'utilisateur
        hashed_password = get_password_hash(user_data.password)
        db_user = UserDB(
            id=str(uuid.uuid4()),
            email=user_data.email,
            hashed_password=hashed_password,
            full_name=user_data.full_name,
            role=user_data.role
        )
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        
        return User.model_validate(db_user)
    
    @staticmethod
    def login_user(db: Session, login_data: UserLogin) -> Token:
        # Trouver l'utilisateur
        user = db.query(UserDB).filter(UserDB.email == login_data.email).first()
        if not user or not verify_password(login_data.password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is inactive"
            )
        
        # Mettre à jour last_login
        user.last_login = datetime.now(timezone.utc)
        db.commit()
        
        # Créer les tokens
        token_data = {
            "user_id": user.id,
            "email": user.email,
            "role": user.role.value
        }
        access_token = create_access_token(token_data)
        refresh_token = create_refresh_token(token_data)
        
        return Token(access_token=access_token, refresh_token=refresh_token)
    
    @staticmethod
    def get_user_by_id(db: Session, user_id: str) -> User:
        user = db.query(UserDB).filter(UserDB.id == user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        return User.model_validate(user)
    
    @staticmethod
    def get_user_by_email(db: Session, email: str) -> User:
        db_user = db.query(UserDB).filter(UserDB.email == email).first()
        if not db_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        return User.model_validate(db_user)
        
    @staticmethod
    def count_specialists(db: Session) -> dict:
        from app.models.user import UserRole
        
        # Compter les utilisateurs actifs avec un rôle de spécialiste (tous les rôles sauf admin)
        count = db.query(UserDB).filter(
            UserDB.is_active == True,
            UserDB.role.in_(['orthodontiste', 'anatomopathologiste', 'oncologue'])
        ).count()
        
        return {"count": count}
