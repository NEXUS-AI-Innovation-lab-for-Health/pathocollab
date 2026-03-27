"""add closed to casestatus enum

Revision ID: 006_add_closed_status
Revises: 005
Create Date: 2026-03-27
"""

from alembic import op


# adapte si besoin
revision = "004_closedCase"
down_revision = "003_discussion"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("ALTER TYPE casestatus ADD VALUE IF NOT EXISTS 'closed'")


def downgrade():
    # PostgreSQL ne supprime pas simplement une valeur d'enum.
    # On laisse vide volontairement.
    pass