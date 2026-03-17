from __future__ import annotations

import asyncio
import logging

from sqlalchemy import select

from app.db import _bg_session_factory
from app.models import Movie
from app.routers.game import _ensure_movie_cast_in_db, _ensure_movie_details_in_db
from app.services.tmdb import TMDBClient

logger = logging.getLogger(__name__)


async def nightly_cache_job(tmdb: TMDBClient, top_n: int = 5000) -> None:
    """Fetch top-N movies by vote count and ensure all are fully cached in the DB.

    Incremental: skips movies where fetched_at IS NOT NULL AND genres IS NOT NULL.
    Uses the shared TMDBClient (with existing _sem concurrency limit).
    """
    logger.info("nightly_cache_job starting: top_n=%d", top_n)
    page = 1
    collected: list[int] = []

    while len(collected) < top_n:
        try:
            r = await tmdb._client.get(
                "/discover/movie",
                params={
                    "sort_by": "vote_count.desc",
                    "vote_count.gte": 500,
                    "page": page,
                },
            )
            r.raise_for_status()
        except Exception as exc:
            logger.error("nightly_cache_job: TMDB discover failed on page %d: %s", page, exc)
            break

        results = r.json().get("results", [])
        if not results:
            break
        collected.extend(item["id"] for item in results)
        page += 1

    tmdb_ids = collected[:top_n]
    logger.info("nightly_cache_job: collected %d TMDB IDs", len(tmdb_ids))

    async with _bg_session_factory() as db:
        # Determine which movies already have full cache (fetched_at + genres both present)
        already = await db.execute(
            select(Movie.tmdb_id).where(
                Movie.tmdb_id.in_(tmdb_ids),
                Movie.fetched_at.isnot(None),
                Movie.genres.isnot(None),
            )
        )
        cached_ids = {row[0] for row in already.all()}
        to_fetch = [tid for tid in tmdb_ids if tid not in cached_ids]
        logger.info("nightly_cache_job: %d movies need enrichment", len(to_fetch))

        for tmdb_id in to_fetch:
            await _ensure_movie_cast_in_db(tmdb_id, tmdb, db)
            await _ensure_movie_details_in_db([tmdb_id], tmdb, db)
            await asyncio.sleep(0.05)  # stay well within TMDB 40 req/s limit

    logger.info("nightly_cache_job complete")
