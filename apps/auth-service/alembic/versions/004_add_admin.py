from alembic import op
import sqlalchemy as sa
import uuid
from datetime import datetime, timezone
from passlib.context import CryptContext

revision = "004"
down_revision = "003"
branch_labels = None
depends_on = None

def upgrade():
    conn = op.get_bind()

    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    hashed_password = pwd_context.hash("admin1234")

    existing_user = conn.execute(
        sa.text("SELECT id FROM users WHERE email = :email"),
        {"email": "admin@gmail.com"}
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
                "email": "admin@gmail.com",
                "hashed_password": hashed_password,
                "full_name": "Administrateur",
                "role": "admin",
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
        {"email": "admin@gmail.com"}
    )