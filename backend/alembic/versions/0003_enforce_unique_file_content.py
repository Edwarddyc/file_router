"""Enforce one registered file record per content hash.

Revision ID: 0003
Revises: 0002
Create Date: 2026-09-24
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "file_records",
        sa.Column(
            "content_duplicate_detected",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )

    connection = op.get_bind()
    duplicate_groups = connection.execute(
        sa.text(
            """
            SELECT sha256
            FROM file_records
            WHERE sha256 IS NOT NULL
            GROUP BY sha256
            HAVING COUNT(*) > 1
            """
        )
    ).scalars().all()
    for sha256 in duplicate_groups:
        rows = connection.execute(
            sa.text(
                """
                SELECT file_id
                FROM file_records
                WHERE sha256 = :sha256
                ORDER BY created_at ASC, file_id ASC
                """
            ),
            {"sha256": sha256},
        ).scalars().all()
        canonical_file_id, *duplicate_file_ids = rows
        connection.execute(
            sa.text(
                """
                UPDATE file_records
                SET content_duplicate_detected = :detected,
                    hidden_from_file_lists = :visible,
                    duplicate_of_file_id = NULL
                WHERE file_id = :file_id
                """
            ),
            {"detected": True, "visible": False, "file_id": canonical_file_id},
        )
        for duplicate_file_id in duplicate_file_ids:
            connection.execute(
                sa.text("DELETE FROM file_records WHERE file_id = :file_id"),
                {"file_id": duplicate_file_id},
            )

    op.create_index("uq_file_records_sha256", "file_records", ["sha256"], unique=True)


def downgrade() -> None:
    op.drop_index("uq_file_records_sha256", table_name="file_records")
    op.drop_column("file_records", "content_duplicate_detected")
