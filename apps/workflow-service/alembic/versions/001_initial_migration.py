"""initial workflow service schema

Revision ID: 001_initial_migration
Revises:
Create Date: 2026-03-09
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "001_initial_migration"
down_revision = None
branch_labels = None
depends_on = None


notification_type = sa.Enum(
    "CASE_ASSIGNED",
    "TURN_READY",
    "CASE_COMPLETED",
    "SPECIALIST_REQUESTED",
    "COMMENT_ADDED",
    name="notification_type",
)


def upgrade() -> None:
    bind = op.get_bind()
    notification_type.create(bind, checkfirst=True)

    op.create_table(
        "workflows",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("case_id", sa.String(), nullable=False),
        sa.Column("specialists_order", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("current_step", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("workflow_engine", sa.String(), nullable=False, server_default="local"),
        sa.Column("olga_workflow_code", sa.String(), nullable=True),
        sa.Column("olga_session_id", sa.String(), nullable=True),
        sa.Column("olga_status", sa.String(), nullable=True),
        sa.Column("is_completed", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("case_id"),
    )
    op.create_index(op.f("ix_workflows_case_id"), "workflows", ["case_id"], unique=False)
    op.create_index(op.f("ix_workflows_olga_session_id"), "workflows", ["olga_session_id"], unique=False)

    op.create_table(
        "notifications",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("case_id", sa.String(), nullable=False),
        sa.Column("type", notification_type, nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("is_read", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_notifications_case_id"), "notifications", ["case_id"], unique=False)
    op.create_index(op.f("ix_notifications_user_id"), "notifications", ["user_id"], unique=False)



def downgrade() -> None:
    op.drop_index(op.f("ix_notifications_user_id"), table_name="notifications")
    op.drop_index(op.f("ix_notifications_case_id"), table_name="notifications")
    op.drop_table("notifications")

    op.drop_index(op.f("ix_workflows_olga_session_id"), table_name="workflows")
    op.drop_index(op.f("ix_workflows_case_id"), table_name="workflows")
    op.drop_table("workflows")

    bind = op.get_bind()
    notification_type.drop(bind, checkfirst=True)
