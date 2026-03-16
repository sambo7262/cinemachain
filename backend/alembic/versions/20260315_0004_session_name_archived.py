"""add name and archived_at to game_sessions

Revision ID: 0004
Revises: 0003
Create Date: 2026-03-15
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "game_sessions",
        sa.Column("name", sa.String(100), nullable=False, server_default=""),
    )
    op.add_column(
        "game_sessions",
        sa.Column("archived_at", sa.DateTime(), nullable=True),
    )
    # Backfill existing rows with a generated name to avoid empty-string collisions
    op.execute(
        "UPDATE game_sessions SET name = 'Session ' || id::text WHERE name = ''"
    )
    # Partial unique index: name must be unique among non-archived, non-ended sessions
    op.execute(
        "CREATE UNIQUE INDEX uq_game_sessions_name_active "
        "ON game_sessions (name) "
        "WHERE status NOT IN ('archived', 'ended')"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS uq_game_sessions_name_active")
    op.drop_column("game_sessions", "archived_at")
    op.drop_column("game_sessions", "name")
