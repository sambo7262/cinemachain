"""add filmography_fetched_at timestamp to actors

Revision ID: 0019
Revises: 0018
Create Date: 2026-05-29

Adds a nullable TIMESTAMP column tracking when an actor's full filmography was last
fetched from TMDB. NULL = no timestamp yet under the new TTL regime = treated as
stale by the on-demand refresh path in _ensure_actor_credits_in_db.

No backfill: leaving existing rows at NULL lets the on-demand path self-heal lazily as
users interact with each actor, and the nightly cache job catches the rest within 24h.
Backfilling to NOW() would mask staleness for up to 14 days post-deploy; backfilling to
an old date would cause a thundering herd against TMDB. NULL is the right default.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0019"
down_revision: Union[str, None] = "0018"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "actors",
        sa.Column("filmography_fetched_at", sa.DateTime(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("actors", "filmography_fetched_at")
