"""Add rating to watch_events

Revision ID: 0014
Revises: 0013
Create Date: 2026-04-01
"""
from alembic import op
import sqlalchemy as sa

revision = "0014"
down_revision = "0013"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("watch_events", sa.Column("rating", sa.Integer(), nullable=True))


def downgrade():
    op.drop_column("watch_events", "rating")
