"""Add mdblist_fetched_at to movies

Revision ID: 0012
Revises: 0011
Create Date: 2026-04-01
"""
from alembic import op
import sqlalchemy as sa

revision = "0012"
down_revision = "0011"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("movies", sa.Column("mdblist_fetched_at", sa.DateTime(), nullable=True))


def downgrade():
    op.drop_column("movies", "mdblist_fetched_at")
