"""Add MDBList expansion columns: imdb_id, imdb_rating, metacritic_score, letterboxd_score, mdb_avg_score

Revision ID: 0011
Revises: 0010
Create Date: 2026-04-01
"""
from typing import Union
import sqlalchemy as sa
from alembic import op

revision: str = "0011"
down_revision: Union[str, None] = "0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("movies", sa.Column("imdb_id", sa.String(20), nullable=True))
    op.add_column("movies", sa.Column("imdb_rating", sa.Float(), nullable=True))
    op.add_column("movies", sa.Column("metacritic_score", sa.Integer(), nullable=True))
    op.add_column("movies", sa.Column("letterboxd_score", sa.Float(), nullable=True))
    op.add_column("movies", sa.Column("mdb_avg_score", sa.Float(), nullable=True))
    # Reset rt_score to NULL so backfill re-fetches all movies and populates new fields
    op.execute("UPDATE movies SET rt_score = NULL")


def downgrade() -> None:
    op.drop_column("movies", "mdb_avg_score")
    op.drop_column("movies", "letterboxd_score")
    op.drop_column("movies", "metacritic_score")
    op.drop_column("movies", "imdb_rating")
    op.drop_column("movies", "imdb_id")
