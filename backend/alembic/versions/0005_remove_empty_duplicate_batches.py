"""Remove empty batches left by legacy duplicate file records.

Revision ID: 0005
Revises: 0004
Create Date: 2026-09-24
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        DELETE FROM ingest_batches
        WHERE NOT EXISTS (
            SELECT 1
            FROM file_records
            WHERE file_records.batch_id = ingest_batches.batch_id
        )
        """
    )


def downgrade() -> None:
    # Removed empty batches contain no file data and cannot be reconstructed.
    pass
