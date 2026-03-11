from alembic import op
import sqlalchemy as sa
import uuid
from datetime import datetime, timezone

revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None

def upgrade():
    conn = op.get_bind()

    existing_user = conn.execute(
        sa.text("SELECT id FROM users WHERE email = :email"),
        {"email": "dr.smith@pixtral.local"}
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
                    updated_at,
                    last_login
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
                    :updated_at,
                    :last_login
                )
            """),
            {
                "id": str(uuid.uuid4()),
                "email": "dr.smith@pixtral.local",
                "hashed_password": "A_REMPLACER_PAR_UN_VRAI_HASH",
                "full_name": "Dr. Smith",
                "role": "anatomopathologiste",
                "is_active": True,
                "is_verified": True,
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc),
                "last_login": None,
            }
        )

def downgrade():
    conn = op.get_bind()
    conn.execute(
        sa.text("DELETE FROM users WHERE email = :email"),
        {"email": "dr.smith@pixtral.local"}
    )