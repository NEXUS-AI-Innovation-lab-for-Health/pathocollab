from alembic import op
import sqlalchemy as sa

revision = "003_discussion"
down_revision = "002_seed_patients"
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        "discussion_messages",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("case_id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["case_id"], ["cases.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_discussion_messages_case_id"), "discussion_messages", ["case_id"], unique=False)
    op.create_index(op.f("ix_discussion_messages_user_id"), "discussion_messages", ["user_id"], unique=False)


def downgrade():
    op.drop_index(op.f("ix_discussion_messages_user_id"), table_name="discussion_messages")
    op.drop_index(op.f("ix_discussion_messages_case_id"), table_name="discussion_messages")
    op.drop_table("discussion_messages")