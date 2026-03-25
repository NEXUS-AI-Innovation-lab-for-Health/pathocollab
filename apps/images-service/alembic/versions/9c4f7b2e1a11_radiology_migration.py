"""add radiology table and extend annotations

Revision ID: add_radiology_and_annotation_fields
Revises: 6e853361ff0d
Create Date: 2026-03-24
"""

from alembic import op
import sqlalchemy as sa


revision = "9c4f7b2e1a11"
down_revision = "6e853361ff0d"
branch_labels = None
depends_on = None


def upgrade():
    # ---- annotations: ajouter uniquement les colonnes manquantes ----
    with op.batch_alter_table("annotations") as batch_op:
        batch_op.add_column(sa.Column("owner_name", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("severity", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("category", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("description", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("recommendation", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("tags", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("stroke_color", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("fill_color", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("stroke_width", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True))

    op.execute("UPDATE annotations SET updated_at = created_at WHERE updated_at IS NULL")

    with op.batch_alter_table("annotations") as batch_op:
        batch_op.alter_column("updated_at", nullable=False)

    # ---- radiology_series_links ----
    op.create_table(
        "radiology_series_links",
        sa.Column("id", sa.String(), primary_key=True, nullable=False),
        sa.Column("app_patient_id", sa.String(), nullable=False),
        sa.Column("uploaded_by", sa.String(), nullable=False),

        sa.Column("orthanc_patient_id", sa.String(), nullable=False),
        sa.Column("orthanc_study_id", sa.String(), nullable=False),
        sa.Column("orthanc_series_id", sa.String(), nullable=False),
        sa.Column("preview_instance_id", sa.String(), nullable=True),

        sa.Column("patient_name", sa.String(), nullable=True),
        sa.Column("dicom_patient_id", sa.String(), nullable=True),
        sa.Column("study_instance_uid", sa.String(), nullable=True),
        sa.Column("series_instance_uid", sa.String(), nullable=True),

        sa.Column("modality", sa.String(), nullable=True),
        sa.Column("study_date", sa.String(), nullable=True),
        sa.Column("study_description", sa.Text(), nullable=True),
        sa.Column("series_description", sa.Text(), nullable=True),
        sa.Column("instances_count", sa.Integer(), nullable=False, server_default="0"),

        sa.Column("raw_minio_prefix", sa.String(), nullable=True),

        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_index(
        "ix_radiology_series_links_app_patient_id",
        "radiology_series_links",
        ["app_patient_id"],
    )
    op.create_index(
        "ix_radiology_series_links_orthanc_patient_id",
        "radiology_series_links",
        ["orthanc_patient_id"],
    )
    op.create_index(
        "ix_radiology_series_links_orthanc_study_id",
        "radiology_series_links",
        ["orthanc_study_id"],
    )
    op.create_index(
        "ix_radiology_series_links_orthanc_series_id",
        "radiology_series_links",
        ["orthanc_series_id"],
    )


def downgrade():
    op.drop_index(
        "ix_radiology_series_links_orthanc_series_id",
        table_name="radiology_series_links",
    )
    op.drop_index(
        "ix_radiology_series_links_orthanc_study_id",
        table_name="radiology_series_links",
    )
    op.drop_index(
        "ix_radiology_series_links_orthanc_patient_id",
        table_name="radiology_series_links",
    )
    op.drop_index(
        "ix_radiology_series_links_app_patient_id",
        table_name="radiology_series_links",
    )
    op.drop_table("radiology_series_links")

    with op.batch_alter_table("annotations") as batch_op:
        batch_op.drop_column("updated_at")
        batch_op.drop_column("stroke_width")
        batch_op.drop_column("fill_color")
        batch_op.drop_column("stroke_color")
        batch_op.drop_column("tags")
        batch_op.drop_column("recommendation")
        batch_op.drop_column("description")
        batch_op.drop_column("category")
        batch_op.drop_column("severity")
        batch_op.drop_column("owner_name")