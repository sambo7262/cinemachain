"""initial_data_schema

Revision ID: 20260315_0001
Revises:
Create Date: 2026-03-15 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "20260315_0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # movies table — no FK dependencies
    op.create_table(
        "movies",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tmdb_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("year", sa.Integer(), nullable=True),
        sa.Column("poster_path", sa.String(length=512), nullable=True),
        sa.Column("vote_average", sa.Float(), nullable=True),
        sa.Column("genres", sa.String(length=512), nullable=True),
        sa.Column("fetched_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tmdb_id"),
    )
    op.create_index(op.f("ix_movies_tmdb_id"), "movies", ["tmdb_id"], unique=True)

    # actors table — no FK dependencies
    op.create_table(
        "actors",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tmdb_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("profile_path", sa.String(length=512), nullable=True),
        sa.Column("fetched_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tmdb_id"),
    )
    op.create_index(op.f("ix_actors_tmdb_id"), "actors", ["tmdb_id"], unique=True)

    # credits table — FK to movies and actors
    op.create_table(
        "credits",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("movie_id", sa.Integer(), nullable=False),
        sa.Column("actor_id", sa.Integer(), nullable=False),
        sa.Column("character", sa.String(length=255), nullable=True),
        sa.Column("order", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["actor_id"], ["actors.id"]),
        sa.ForeignKeyConstraint(["movie_id"], ["movies.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("movie_id", "actor_id"),
    )
    op.create_index(op.f("ix_credits_actor_id"), "credits", ["actor_id"], unique=False)
    op.create_index(op.f("ix_credits_movie_id"), "credits", ["movie_id"], unique=False)

    # watch_events table — FK to movies (nullable)
    op.create_table(
        "watch_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tmdb_id", sa.Integer(), nullable=False),
        sa.Column("movie_id", sa.Integer(), nullable=True),
        sa.Column("source", sa.String(length=50), nullable=False),
        sa.Column("watched_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["movie_id"], ["movies.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tmdb_id"),
    )
    op.create_index(op.f("ix_watch_events_tmdb_id"), "watch_events", ["tmdb_id"], unique=False)


def downgrade() -> None:
    # Drop in reverse FK dependency order
    op.drop_index(op.f("ix_watch_events_tmdb_id"), table_name="watch_events")
    op.drop_table("watch_events")

    op.drop_index(op.f("ix_credits_movie_id"), table_name="credits")
    op.drop_index(op.f("ix_credits_actor_id"), table_name="credits")
    op.drop_table("credits")

    op.drop_index(op.f("ix_actors_tmdb_id"), table_name="actors")
    op.drop_table("actors")

    op.drop_index(op.f("ix_movies_tmdb_id"), table_name="movies")
    op.drop_table("movies")
