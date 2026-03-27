from alembic import op
import sqlalchemy as sa
from passlib.context import CryptContext
import uuid
from datetime import datetime, timezone

revision = "005"
down_revision = "004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()

    # IMPORTANT : l'ajout d'une valeur d'enum PostgreSQL
    # doit être committé avant de pouvoir être utilisé.
    with op.get_context().autocommit_block():
        op.execute(
            "ALTER TYPE userrole ADD VALUE IF NOT EXISTS 'medecin_generaliste'"
        )

    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    now = datetime.now(timezone.utc)

    users_to_add = [
        {
            "id": str(uuid.uuid4()),
            "email": "alice@gmail.com",
            "hashed_password": pwd_context.hash("alice1234"),
            "full_name": "Dr. Alice",
            "role": "medecin_generaliste",
            "is_active": True,
            "is_verified": True,
            "created_at": now,
            "updated_at": now,
            "last_login": None,
        },
        {
            "id": str(uuid.uuid4()),
            "email": "paul@gmail.com",
            "hashed_password": pwd_context.hash("paul1234"),
            "full_name": "Dr. Paul",
            "role": "medecin_generaliste",
            "is_active": True,
            "is_verified": True,
            "created_at": now,
            "updated_at": now,
            "last_login": None,
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
                user,
            )


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(
        sa.text("""
            DELETE FROM users
            WHERE email IN ('alice@gmail.com', 'paul@gmail.com')
        """)
    )