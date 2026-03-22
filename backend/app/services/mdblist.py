"""MDBList API client for fetching Rotten Tomatoes scores."""
from __future__ import annotations

import logging
import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Movie
from app.services import settings_service

logger = logging.getLogger(__name__)

MDBLIST_API_URL = "https://mdblist.com/api/"


async def fetch_rt_scores(
    tmdb_ids: list[int],
    db: AsyncSession,
) -> None:
    """Fetch RT scores from MDBList for movies where rt_score is NULL.

    Fetches synchronously (one request per movie). Results are written
    directly to the Movie rows in the DB. Caller must commit.

    Does nothing if mdblist_api_key is not configured.
    """
    api_key = await settings_service.get_setting(db, "mdblist_api_key")
    if not api_key:
        return

    # Only fetch for movies that don't have a score yet
    result = await db.execute(
        select(Movie).where(
            Movie.tmdb_id.in_(tmdb_ids),
            Movie.rt_score.is_(None),
        )
    )
    movies_to_fetch = result.scalars().all()
    if not movies_to_fetch:
        return

    async with httpx.AsyncClient(timeout=10.0) as client:
        for movie in movies_to_fetch:
            try:
                resp = await client.get(
                    MDBLIST_API_URL,
                    params={"apikey": api_key, "tm": movie.tmdb_id},
                )
                if resp.status_code != 200:
                    logger.warning(
                        "MDBList API returned %d for tmdb_id=%d",
                        resp.status_code, movie.tmdb_id,
                    )
                    continue

                data = resp.json()
                ratings = data.get("ratings", [])

                tomatometer = None
                audience = None
                for r in ratings:
                    if r.get("source") == "tomatoes":
                        tomatometer = r.get("value")
                    elif r.get("source") == "tomatoesaudience":
                        audience = r.get("value")

                # Store scores. rt_score = 0 means "fetched, no RT data available"
                # (distinguishes from None which means "never fetched").
                movie.rt_score = tomatometer if tomatometer is not None else 0
                movie.rt_audience_score = audience if audience is not None else 0

            except Exception:
                logger.exception(
                    "Failed to fetch MDBList scores for tmdb_id=%d", movie.tmdb_id
                )
                # Don't set rt_score — will retry next time
                continue
