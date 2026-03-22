"""add rt_score and rt_audience_score to movies

Revision ID: 0008
Revises: 0007
Create Date: 2026-03-22
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0008"
down_revision: Union[str, None] = "0007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("movies", sa.Column("rt_score", sa.Integer(), nullable=True))
    op.add_column("movies", sa.Column("rt_audience_score", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("movies", "rt_audience_score")
    op.drop_column("movies", "rt_score")
