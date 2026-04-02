"""add global_saves table

Revision ID: 0017
Revises: 0016
Create Date: 2026-04-01

Phase 16: session-independent bookmarks for Watch History star/save action.
A movie saved from Watch History surfaces as saved in any game session's eligible-movies list.
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0017"
down_revision = "0016"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "global_saves",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tmdb_id", sa.Integer(), nullable=False, unique=True),
        sa.Column("saved_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_global_saves_tmdb_id", "global_saves", ["tmdb_id"])


def downgrade() -> None:
    op.drop_index("ix_global_saves_tmdb_id", table_name="global_saves")
    op.drop_table("global_saves")
