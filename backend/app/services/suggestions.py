from __future__ import annotations

import logging
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import _bg_session_factory
from app.models import Movie, WatchEvent
from app.services import settings_service
from app.services.tmdb import TMDBClient
from app.utils.masking import scrub_traceback

logger = logging.getLogger(__name__)


async def fetch_and_cache_recommendations(
    tmdb_id: int, db: AsyncSession, tmdb: TMDBClient
) -> list[int]:
    """Return cached TMDB recommendation IDs for a movie, fetching if not yet cached.

    Returns [] if movie not in DB or TMDB returns no results.
    Writes [] to cache after a successful fetch with no results — prevents re-fetching.
    """
    result = await db.execute(select(Movie).where(Movie.tmdb_id == tmdb_id))
    movie = result.scalar_one_or_none()
    if movie is None:
        return []
    if movie.tmdb_recommendations is not None:
        return movie.tmdb_recommendations  # cache hit

    # Cache miss — fetch from TMDB
    try:
        data = await tmdb.fetch_recommendations(tmdb_id)
        rec_ids = [r["id"] for r in data.get("results", [])]
    except Exception as exc:
        safe_tb = scrub_traceback(exc)
        logger.error(
            "fetch_and_cache_recommendations: TMDB call failed tmdb_id=%d\n%s",
            tmdb_id, safe_tb,
        )
        return []

    # Always write the list (even []) to mark as fetched
    movie.tmdb_recommendations = rec_ids
    await db.commit()
    return rec_ids


async def get_session_suggestions(
    db: AsyncSession, tmdb: TMDBClient, n: int = 5
) -> list[int]:
    """Return TMDB-recommended movie IDs ranked by frequency across the last N watched movies.

    Uses a global sliding window — not scoped to any session.
    Seed movies themselves are excluded from the returned list.
    """
    result = await db.execute(
        select(WatchEvent.tmdb_id)
        .order_by(WatchEvent.watched_at.desc())
        .limit(n)
    )
    seed_tmdb_ids = [row[0] for row in result.all()]
    if not seed_tmdb_ids:
        return []

    seed_set = set(seed_tmdb_ids)
    freq: dict[int, int] = {}
    for seed_id in seed_tmdb_ids:
        recs = await fetch_and_cache_recommendations(seed_id, db, tmdb)
        for rec_id in recs:
            if rec_id not in seed_set:  # exclude seeds from results
                freq[rec_id] = freq.get(rec_id, 0) + 1

    # Require freq >= 2 when there are enough seeds for meaningful overlap.
    # With < 3 seeds, TMDB rec lists of ~20 rarely intersect — fall back to freq >= 1
    # so the feature still surfaces something useful early in a session.
    min_freq = 2 if len(seed_tmdb_ids) >= 3 else 1
    return sorted([k for k, v in freq.items() if v >= min_freq], key=lambda k: freq[k], reverse=True)


async def _update_session_suggestions(session_id: int) -> None:
    """Background task: warm recommendation cache for the most recently watched movie.

    Instantiates its own TMDBClient (no request context available in BG tasks).
    Reads api_key and seed_count from app_settings via settings_service.
    """
    try:
        async with _bg_session_factory() as db:
            api_key = await settings_service.get_setting(db, "tmdb_api_key")
            if not api_key:
                return
            n_str = await settings_service.get_setting(db, "tmdb_suggestions_seed_count")
            n = int(n_str or "5")

            tmdb = TMDBClient(api_key)
            try:
                # Warm cache for the seed window — this caches any uncached seed movies
                await get_session_suggestions(db, tmdb, n)
            finally:
                await tmdb.close()
    except Exception as exc:
        safe_tb = scrub_traceback(exc)
        logger.error(
            "_update_session_suggestions: unexpected error session_id=%d\n%s",
            session_id, safe_tb,
        )
