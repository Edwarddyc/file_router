"""Remove persisted UI-only duplicate state.

Revision ID: 0004
Revises: 0003
Create Date: 2026-09-24
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_column("file_records", "hidden_from_file_lists")
    op.drop_column("file_records", "content_duplicate_detected")


def downgrade() -> None:
    op.add_column(
        "file_records",
        sa.Column("content_duplicate_detected", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "file_records",
        sa.Column("hidden_from_file_lists", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
