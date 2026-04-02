"""Add tmdb_recommendations JSON column to movies

Revision ID: 0015
Revises: 0014
Create Date: 2026-04-01
"""
import sqlalchemy as sa
from alembic import op

revision: str = "0015"
down_revision: str = "0014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("movies", sa.Column("tmdb_recommendations", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("movies", "tmdb_recommendations")
