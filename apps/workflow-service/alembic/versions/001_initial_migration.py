"""Initial migration

Revision ID: 001
Revises: 
Create Date: 2026-02-03 16:22:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create workflows table
    op.create_table('workflows',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('case_id', sa.String(), nullable=False),
        sa.Column('current_step', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_workflows_case_id'), 'workflows', ['case_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_workflows_case_id'), table_name='workflows')
    op.drop_table('workflows')
