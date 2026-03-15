"""game session schema

Revision ID: 0002
Revises: 20260315_0001
Create Date: 2026-03-15
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0002"
down_revision: Union[str, None] = "20260315_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add runtime column to movies table
    op.add_column("movies", sa.Column("runtime", sa.Integer(), nullable=True))

    # Create game_sessions table
    op.create_table(
        "game_sessions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("current_movie_tmdb_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create game_session_steps table
    op.create_table(
        "game_session_steps",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("session_id", sa.Integer(), nullable=False),
        sa.Column("step_order", sa.Integer(), nullable=False),
        sa.Column("movie_tmdb_id", sa.Integer(), nullable=False),
        sa.Column("actor_tmdb_id", sa.Integer(), nullable=True),
        sa.Column("actor_name", sa.String(255), nullable=True),
        sa.Column("movie_title", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["session_id"], ["game_sessions.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_game_session_steps_session_id", "game_session_steps", ["session_id"])


def downgrade() -> None:
    op.drop_index("ix_game_session_steps_session_id", table_name="game_session_steps")
    op.drop_table("game_session_steps")
    op.drop_table("game_sessions")
    op.drop_column("movies", "runtime")
