"""Add Dr. Smith user

Revision ID: 002
Revises: 001
Create Date: 2026-02-03 17:08:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.orm import sessionmaker
from passlib.context import CryptContext
import os
import uuid

# revision identifiers, used by Alembic.
revision = '002'
down_revision = '001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Get database URL from environment
    database_url = os.getenv('DATABASE_URL', 'postgresql://pixtral_user:pixtral_pass@postgres:5432/auth_db')
    
    # Create engine and session
    from sqlalchemy import create_engine
    engine = create_engine(database_url)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    # Create password hash
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    hashed_password = pwd_context.hash("password123")  # Mot de passe temporaire
    
    # Insert Dr. Smith user
    with SessionLocal() as session:
        # Check if user already exists
        existing_user = session.execute(
            sa.text("SELECT id FROM users WHERE email = 'dr.smith@pixtral.fr'")
        ).fetchone()
        
        if not existing_user:
            session.execute(
                sa.text("""
                INSERT INTO users (id, email, hashed_password, full_name, role, is_active, is_verified, created_at, updated_at)
                VALUES (
                    :user_id,
                    'dr.smith@pixtral.fr',
                    :hashed_password,
                    'Dr. Smith',
                    'orthodontiste',
                    true,
                    true,
                    NOW(),
                    NOW()
                )
                """),
                {"user_id": str(uuid.uuid4()), "hashed_password": hashed_password}
            )
            session.commit()
            print("✅ Utilisateur Dr. Smith créé avec succès")
        else:
            print("ℹ️ L'utilisateur Dr. Smith existe déjà")


def downgrade() -> None:
    # Remove Dr. Smith user
    database_url = os.getenv('DATABASE_URL', 'postgresql://pixtral_user:pixtral_pass@postgres:5432/auth_db')
    
    from sqlalchemy import create_engine
    engine = create_engine(database_url)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    with SessionLocal() as session:
        session.execute(
            sa.text("DELETE FROM users WHERE email = 'dr.smith@pixtral.fr'")
        )
        session.commit()
        print("✅ Utilisateur Dr. Smith supprimé")
