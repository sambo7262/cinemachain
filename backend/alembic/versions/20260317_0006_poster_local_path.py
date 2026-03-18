"""add poster_local_path to movies

Revision ID: 0006
Revises: 0005
Create Date: 2026-03-17
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0006"
down_revision: Union[str, None] = "0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("movies", sa.Column("poster_local_path", sa.String(255), nullable=True))


def downgrade() -> None:
    op.drop_column("movies", "poster_local_path")
