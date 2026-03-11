from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "001_initial_migration"
down_revision = None
branch_labels = None
depends_on = None


case_status_enum = postgresql.ENUM(
    "pending",
    "in_progress",
    "completed",
    "on_hold",
    name="casestatus",
    create_type=False,
)


def upgrade() -> None:
    op.execute("""
    DO $$
    BEGIN
        IF NOT EXISTS (
            SELECT 1
            FROM pg_type
            WHERE typname = 'casestatus'
        ) THEN
            CREATE TYPE casestatus AS ENUM (
                'pending',
                'in_progress',
                'completed',
                'on_hold'
            );
        END IF;
    END
    $$;
    """)

    op.create_table(
        "patients",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("full_name", sa.String(), nullable=False),
        sa.Column("age", sa.Integer(), nullable=False),
        sa.Column("gender", sa.String(), nullable=False),
        sa.Column("date_of_birth", sa.Date(), nullable=True),
        sa.Column("medical_history", sa.Text(), nullable=True),
        sa.Column("symptoms", sa.Text(), nullable=True),
        sa.Column("imaging_notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "specialists",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("nom", sa.String(), nullable=False),
        sa.Column("prenom", sa.String(), nullable=False),
        sa.Column("specialite", sa.String(), nullable=False),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("disponible", sa.Boolean(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )

    op.create_table(
        "cases",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("patient_id", sa.String(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("status", case_status_enum, nullable=True),
        sa.Column("created_by", sa.String(), nullable=False),
        sa.Column("assigned_specialists", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(op.f("ix_cases_id"), "cases", ["id"], unique=False)
    op.create_index(op.f("ix_cases_patient_id"), "cases", ["patient_id"], unique=False)
    op.create_index(op.f("ix_patients_id"), "patients", ["id"], unique=False)
    op.create_index(op.f("ix_specialists_id"), "specialists", ["id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_specialists_id"), table_name="specialists")
    op.drop_index(op.f("ix_patients_id"), table_name="patients")
    op.drop_index(op.f("ix_cases_patient_id"), table_name="cases")
    op.drop_index(op.f("ix_cases_id"), table_name="cases")

    op.drop_table("cases")
    op.drop_table("specialists")
    op.drop_table("patients")

    op.execute("DROP TYPE IF EXISTS casestatus")