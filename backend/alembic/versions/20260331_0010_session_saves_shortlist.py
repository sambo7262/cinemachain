"""Add session_saves and session_shortlist tables

Revision ID: 0010
Revises: 0009
Create Date: 2026-03-31
"""
from typing import Union
import sqlalchemy as sa
from alembic import op

revision: str = "0010"
down_revision: Union[str, None] = "0009"
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.create_table(
        "session_saves",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("session_id", sa.Integer(), sa.ForeignKey("game_sessions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("tmdb_id", sa.Integer(), nullable=False),
        sa.Column("saved_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
        sa.UniqueConstraint("session_id", "tmdb_id"),
    )
    op.create_table(
        "session_shortlist",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("session_id", sa.Integer(), sa.ForeignKey("game_sessions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("tmdb_id", sa.Integer(), nullable=False),
        sa.UniqueConstraint("session_id", "tmdb_id"),
    )

def downgrade() -> None:
    op.drop_table("session_shortlist")
    op.drop_table("session_saves")
