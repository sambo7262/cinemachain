"""drop mdblist_synced_at from watch_events

Revision ID: 0016
Revises: 0015
Create Date: 2026-04-01

Phase 16 cleanup: removes Phase 14 MDBList watch-sync column.
The rating column (0014) is preserved — it is used by Phase 16 personal ratings.
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0016"
down_revision = "0015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("watch_events") as batch_op:
        batch_op.drop_column("mdblist_synced_at")


def downgrade() -> None:
    with op.batch_alter_table("watch_events") as batch_op:
        batch_op.add_column(sa.Column("mdblist_synced_at", sa.DateTime(), nullable=True))
