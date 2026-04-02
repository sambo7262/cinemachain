"""Add mdblist_synced_at to watch_events

Revision ID: 0013
Revises: 0012
Create Date: 2026-04-01
"""
from alembic import op
import sqlalchemy as sa

revision = "0013"
down_revision = "0012"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("watch_events", sa.Column("mdblist_synced_at", sa.DateTime(), nullable=True))


def downgrade():
    op.drop_column("watch_events", "mdblist_synced_at")
