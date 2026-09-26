"""Create intake registry tables.

Revision ID: 0001
Revises:
Create Date: 2026-09-24
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "ingest_batches",
        sa.Column("batch_id", sa.String(36), primary_key=True),
        sa.Column("project_id", sa.String(200), nullable=False),
        sa.Column("source_kind", sa.String(30), nullable=False),
        sa.Column("source_description", sa.Text(), nullable=True),
        sa.Column("submitted_by", sa.String(200), nullable=True),
        sa.Column("idempotency_key", sa.String(200), nullable=False),
        sa.Column("request_fingerprint", sa.String(64), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("total_count", sa.Integer(), nullable=False),
        sa.Column("registered_count", sa.Integer(), nullable=False),
        sa.Column("failed_count", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("idempotency_key"),
    )
    op.create_index("ix_ingest_batches_project_id", "ingest_batches", ["project_id"])
    op.create_index("ix_ingest_batches_idempotency_key", "ingest_batches", ["idempotency_key"], unique=True)
    op.create_index("ix_ingest_batches_status", "ingest_batches", ["status"])
    op.create_index("ix_ingest_batches_created_at", "ingest_batches", ["created_at"])

    op.create_table(
        "original_blobs",
        sa.Column("sha256", sa.String(64), primary_key=True),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("storage_key", sa.String(300), nullable=False, unique=True),
        sa.Column("detected_media_type", sa.String(200), nullable=True),
        sa.Column("integrity_status", sa.String(30), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "file_records",
        sa.Column("file_id", sa.String(36), primary_key=True),
        sa.Column("batch_id", sa.String(36), sa.ForeignKey("ingest_batches.batch_id"), nullable=False),
        sa.Column("project_id", sa.String(200), nullable=False),
        sa.Column("original_name", sa.Text(), nullable=False),
        sa.Column("display_name", sa.String(500), nullable=False),
        sa.Column("client_media_type", sa.String(200), nullable=True),
        sa.Column("detected_media_type", sa.String(200), nullable=True),
        sa.Column("extension", sa.String(30), nullable=True),
        sa.Column("size_bytes", sa.Integer(), nullable=True),
        sa.Column("sha256", sa.String(64), sa.ForeignKey("original_blobs.sha256"), nullable=True),
        sa.Column("duplicate_of_file_id", sa.String(36), sa.ForeignKey("file_records.file_id"), nullable=True),
        sa.Column("source_uri", sa.Text(), nullable=True),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("failure_code", sa.String(100), nullable=True),
        sa.Column("failure_message", sa.Text(), nullable=True),
        sa.Column("registered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    for column in ("batch_id", "project_id", "extension", "sha256", "status", "created_at"):
        op.create_index(f"ix_file_records_{column}", "file_records", [column])
    op.create_index(
        "ix_file_records_created_file",
        "file_records",
        [sa.text("created_at DESC"), sa.text("file_id DESC")],
    )


def downgrade() -> None:
    op.drop_table("file_records")
    op.drop_table("original_blobs")
    op.drop_table("ingest_batches")
