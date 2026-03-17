"""add vote_count and mpaa_rating to movies

Revision ID: 0005
Revises: 0004
Create Date: 2026-03-16
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0005"
down_revision: Union[str, None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("movies", sa.Column("vote_count", sa.Integer(), nullable=True))
    op.add_column("movies", sa.Column("mpaa_rating", sa.String(10), nullable=True))


def downgrade() -> None:
    op.drop_column("movies", "mpaa_rating")
    op.drop_column("movies", "vote_count")
