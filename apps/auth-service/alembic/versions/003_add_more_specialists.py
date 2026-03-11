"""Add more specialists

Revision ID: 003
Revises: 002
Create Date: 2026-02-03 17:32:00.000000
"""

from alembic import op
import sqlalchemy as sa
from passlib.context import CryptContext
import uuid
from datetime import datetime, timezone

revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()

    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    hashed_password = pwd_context.hash("password123")
    now = datetime.now(timezone.utc)

    users_to_add = [
        {
            "id": str(uuid.uuid4()),
            "email": "dr.johnson@pixtral.fr",
            "hashed_password": hashed_password,
            "full_name": "Dr. Johnson",
            "role": "oncologue",
            "is_active": True,
            "is_verified": True,
            "created_at": now,
            "updated_at": now,
        },
        {
            "id": str(uuid.uuid4()),
            "email": "dr.williams@pixtral.fr",
            "hashed_password": hashed_password,
            "full_name": "Dr. Williams",
            "role": "anatomopathologiste",
            "is_active": True,
            "is_verified": True,
            "created_at": now,
            "updated_at": now,
        },
    ]

    for user in users_to_add:
        existing_user = conn.execute(
            sa.text("SELECT id FROM users WHERE email = :email"),
            {"email": user["email"]},
        ).fetchone()

        if not existing_user:
            conn.execute(
                sa.text("""
                    INSERT INTO users (
                        id,
                        email,
                        hashed_password,
                        full_name,
                        role,
                        is_active,
                        is_verified,
                        created_at,
                        updated_at
                    )
                    VALUES (
                        :id,
                        :email,
                        :hashed_password,
                        :full_name,
                        :role,
                        :is_active,
                        :is_verified,
                        :created_at,
                        :updated_at
                    )
                """),
                user,
            )


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(
        sa.text(
            "DELETE FROM users WHERE email IN ('dr.johnson@pixtral.fr', 'dr.williams@pixtral.fr')"
        )
    )