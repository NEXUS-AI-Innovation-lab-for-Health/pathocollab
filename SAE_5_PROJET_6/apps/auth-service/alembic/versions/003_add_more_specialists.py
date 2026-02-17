"""Add more specialists

Revision ID: 003
Revises: 002
Create Date: 2026-02-03 17:32:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.orm import sessionmaker
from passlib.context import CryptContext
import os
import uuid

# revision identifiers, used by Alembic.
revision = '003'
down_revision = '002'
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
    hashed_password = pwd_context.hash("password123")
    
    # Insert Dr. Johnson
    with SessionLocal() as session:
        existing_user = session.execute(
            sa.text("SELECT id FROM users WHERE email = 'dr.johnson@pixtral.fr'")
        ).fetchone()
        
        if not existing_user:
            session.execute(
                sa.text("""
                INSERT INTO users (id, email, hashed_password, full_name, role, is_active, is_verified, created_at, updated_at)
                VALUES (
                    :user_id,
                    'dr.johnson@pixtral.fr',
                    :hashed_password,
                    'Dr. Johnson',
                    'oncologue',
                    true,
                    true,
                    NOW(),
                    NOW()
                )
                """),
                {"user_id": str(uuid.uuid4()), "hashed_password": hashed_password}
            )
            print("✅ Utilisateur Dr. Johnson créé avec succès")
        
        # Insert Dr. Williams
        existing_user = session.execute(
            sa.text("SELECT id FROM users WHERE email = 'dr.williams@pixtral.fr'")
        ).fetchone()
        
        if not existing_user:
            session.execute(
                sa.text("""
                INSERT INTO users (id, email, hashed_password, full_name, role, is_active, is_verified, created_at, updated_at)
                VALUES (
                    :user_id,
                    'dr.williams@pixtral.fr',
                    :hashed_password,
                    'Dr. Williams',
                    'anatomopathologiste',
                    true,
                    true,
                    NOW(),
                    NOW()
                )
                """),
                {"user_id": str(uuid.uuid4()), "hashed_password": hashed_password}
            )
            print("✅ Utilisateur Dr. Williams créé avec succès")
        
        session.commit()


def downgrade() -> None:
    # Remove Dr. Johnson and Dr. Williams
    database_url = os.getenv('DATABASE_URL', 'postgresql://pixtral_user:pixtral_pass@postgres:5432/auth_db')
    
    from sqlalchemy import create_engine
    engine = create_engine(database_url)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    with SessionLocal() as session:
        session.execute(sa.text("DELETE FROM users WHERE email = 'dr.johnson@pixtral.fr'"))
        session.execute(sa.text("DELETE FROM users WHERE email = 'dr.williams@pixtral.fr'"))
        session.commit()
        print("✅ Utilisateurs Dr. Johnson et Dr. Williams supprimés")
