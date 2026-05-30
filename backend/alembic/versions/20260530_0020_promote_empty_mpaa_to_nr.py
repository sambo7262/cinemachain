"""promote empty mpaa_rating to 'NR' sentinel

Revision ID: 0020
Revises: 0019
Create Date: 2026-05-30

Promotes existing `mpaa_rating = ''` rows to `mpaa_rating = 'NR'` so the new
positive-sentinel pattern in services/cache.py:_backfill_mpaa_pass takes immediate
effect on deploy. The nightly backfill query now targets `mpaa_rating IS NULL` only;
without this migration, the existing ~33k empty-string rows would be permanently
invisible to the backfill (correct outcome) but the OLD query would still re-fetch
them every night until the data settles. Promoting in one shot makes the cutover
atomic.

Data-only migration — no schema change. Downgrade reverts 'NR' → '' for symmetry.
Edge case: a future TMDB response legitimately returning "NR" as a classification
becomes indistinguishable from this sentinel; both render as "NR" to the user, so no
observable behavioural delta (see 23-CONTEXT.md Decision 6).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa  # noqa: F401  (parity with Phase 22 file)

revision: str = "0020"
down_revision: Union[str, None] = "0019"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("UPDATE movies SET mpaa_rating = 'NR' WHERE mpaa_rating = ''")


def downgrade() -> None:
    op.execute("UPDATE movies SET mpaa_rating = '' WHERE mpaa_rating = 'NR'")
