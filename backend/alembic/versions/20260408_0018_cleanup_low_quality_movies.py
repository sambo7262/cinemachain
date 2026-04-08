"""one-time cleanup: remove low-quality movies

Revision ID: 0018
Revises: 0017
Create Date: 2026-04-08

Purges movies matching quality filters:
- vote_count < 5
- runtime < 40 minutes (non-documentaries only)
- TV Movie genre
- Ghost entries (no year and no vote_count)

Protects movies referenced by watch_events, session_saves, session_shortlist,
or game_session_steps. Deletes credits first to satisfy FK constraints.
"""
from __future__ import annotations

from alembic import op
from sqlalchemy import text

revision = "0018"
down_revision = "0017"
branch_labels = None
depends_on = None

VOTE_THRESHOLD = 5
SHORT_RUNTIME_LIMIT = 40


def upgrade() -> None:
    conn = op.get_bind()

    # Collect protected tmdb_ids — movies the user has interacted with
    protected: set[int] = set()
    for query in [
        "SELECT DISTINCT tmdb_id FROM watch_events",
        "SELECT DISTINCT tmdb_id FROM session_saves",
        "SELECT DISTINCT tmdb_id FROM session_shortlist",
        "SELECT DISTINCT movie_tmdb_id FROM game_session_steps",
    ]:
        rows = conn.execute(text(query))
        protected.update(row[0] for row in rows)

    # Find movies to delete — iterate all rows and apply filters in Python
    all_movies = conn.execute(text(
        "SELECT id, tmdb_id, vote_count, runtime, genres, year FROM movies"
    ))
    to_delete: list[int] = []
    for mid, tmdb_id, vc, runtime, genres, year in all_movies:
        if tmdb_id in protected:
            continue

        # Ghost entry: no year and no votes
        if year is None and (vc is None or vc == 0):
            to_delete.append(mid)
            continue

        # Below vote threshold
        if vc is not None and vc < VOTE_THRESHOLD:
            to_delete.append(mid)
            continue

        # Short non-documentary (only when runtime is known)
        if runtime is not None and runtime < SHORT_RUNTIME_LIMIT and genres is not None:
            if "Documentary" not in genres:
                to_delete.append(mid)
                continue

        # TV Movie (only when genres are enriched)
        if genres is not None and "TV Movie" in genres:
            to_delete.append(mid)
            continue

    if not to_delete:
        return

    # Batch delete in chunks to avoid overly large IN clauses
    chunk_size = 500
    for i in range(0, len(to_delete), chunk_size):
        chunk = to_delete[i : i + chunk_size]
        placeholders = ",".join(str(x) for x in chunk)
        conn.execute(text(f"DELETE FROM credits WHERE movie_id IN ({placeholders})"))
        conn.execute(text(f"DELETE FROM movies WHERE id IN ({placeholders})"))


def downgrade() -> None:
    # Data deletion is not reversible
    pass
