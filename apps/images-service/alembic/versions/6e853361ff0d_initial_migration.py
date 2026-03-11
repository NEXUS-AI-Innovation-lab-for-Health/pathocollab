"""Initial migration

Revision ID: 6e853361ff0d
Revises:
Create Date: 2025-12-05 12:06:18.397785
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "6e853361ff0d"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "images",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("case_id", sa.String(), nullable=False),
        sa.Column("filename", sa.String(), nullable=False),
        sa.Column("minio_path", sa.String(), nullable=False),
        sa.Column("mime_type", sa.String(), nullable=False),
        sa.Column("file_size", sa.Integer(), nullable=False),
        sa.Column("width", sa.Integer(), nullable=True),
        sa.Column("height", sa.Integer(), nullable=True),
        sa.Column("uploaded_by", sa.String(), nullable=False),
        sa.Column("is_encrypted", sa.Boolean(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("minio_path"),
    )
    op.create_index(op.f("ix_images_id"), "images", ["id"], unique=False)
    op.create_index(op.f("ix_images_case_id"), "images", ["case_id"], unique=False)

    op.create_table(
        "annotations",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("image_id", sa.String(), nullable=False),
        sa.Column("case_id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column(
            "type",
            sa.Enum("manual", "ai_detected", "ai_assisted", name="annotationtype"),
            nullable=True,
        ),
        sa.Column("coordinates", sa.Text(), nullable=False),
        sa.Column("label", sa.String(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_annotations_image_id"), "annotations", ["image_id"], unique=False)
    op.create_index(op.f("ix_annotations_case_id"), "annotations", ["case_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_annotations_case_id"), table_name="annotations")
    op.drop_index(op.f("ix_annotations_image_id"), table_name="annotations")
    op.drop_table("annotations")

    op.drop_index(op.f("ix_images_case_id"), table_name="images")
    op.drop_index(op.f("ix_images_id"), table_name="images")
    op.drop_table("images")

    op.execute("DROP TYPE IF EXISTS annotationtype")