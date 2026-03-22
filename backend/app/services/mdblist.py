"""MDBList API client for fetching Rotten Tomatoes scores."""
from __future__ import annotations

import asyncio
import logging
import httpx
from sqlalchemy import select, or_
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

    # Cap per-request fetches — generous limit for paid tier (10k/day)
    MAX_PER_REQUEST = 100
    movies_to_fetch = list(movies_to_fetch)[:MAX_PER_REQUEST]

    async with httpx.AsyncClient(timeout=10.0) as client:
        for movie in movies_to_fetch:
            try:
                resp = await client.get(
                    MDBLIST_API_URL,
                    params={"apikey": api_key, "tm": movie.tmdb_id},
                )
                if resp.status_code == 429:
                    logger.warning("MDBList API rate limited (429) — stopping batch")
                    break  # stop entire batch; don't mark these movies so they retry later
                if resp.status_code not in (200, 404):
                    logger.warning(
                        "MDBList API returned %d for tmdb_id=%d",
                        resp.status_code, movie.tmdb_id,
                    )
                    continue
                if resp.status_code == 404:
                    # Movie not in MDBList — store sentinel so we don't retry
                    movie.rt_score = 0
                    movie.rt_audience_score = 0
                    continue

                data = resp.json()
                ratings = data.get("ratings", [])

                tomatometer = None
                audience = None
                for r in ratings:
                    src = r.get("source", "")
                    if src in ("tomatoes", "tomatometr"):
                        tomatometer = r.get("value")
                    elif src in ("tomatoesaudience", "tomatoesau"):
                        audience = r.get("value")

                if tomatometer is None and ratings:
                    sources = [r.get("source") for r in ratings]
                    logger.debug(
                        "MDBList tmdb_id=%d: no RT score found. Available sources: %s",
                        movie.tmdb_id, sources,
                    )

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


async def _fetch_and_store_rt(movie: Movie, client: httpx.AsyncClient, api_key: str) -> bool:
    """Fetch RT scores for a single movie. Returns False if rate-limited (caller should stop)."""
    try:
        resp = await client.get(MDBLIST_API_URL, params={"apikey": api_key, "tm": movie.tmdb_id})
        if resp.status_code == 429:
            logger.warning("MDBList rate limited (429) — stopping nightly backfill")
            return False
        if resp.status_code == 404:
            movie.rt_score = 0
            movie.rt_audience_score = 0
            return True
        if resp.status_code != 200:
            logger.warning("MDBList returned %d for tmdb_id=%d", resp.status_code, movie.tmdb_id)
            return True

        data = resp.json()
        ratings = data.get("ratings", [])
        tomatometer = None
        audience = None
        for r in ratings:
            src = r.get("source", "")
            if src in ("tomatoes", "tomatometr"):
                tomatometer = r.get("value")
            elif src in ("tomatoesaudience", "tomatoesau"):
                audience = r.get("value")

        if tomatometer is None and ratings:
            logger.debug("MDBList tmdb_id=%d: no RT score. Sources: %s", movie.tmdb_id, [r.get("source") for r in ratings])

        movie.rt_score = tomatometer if tomatometer is not None else 0
        movie.rt_audience_score = audience if audience is not None else 0
        return True
    except Exception:
        logger.exception("Failed to fetch MDBList scores for tmdb_id=%d", movie.tmdb_id)
        return True  # don't stop the batch on network errors


async def backfill_rt_scores(db: AsyncSession, limit: int = 500) -> None:
    """Nightly pass: fetch RT scores for movies with NULL or sentinel (0) rt_score.

    Unlike fetch_rt_scores (on-demand), this also retries the 0-sentinel so that
    movies which returned no RT data on a previous attempt get a second chance.
    Stops immediately on 429 to preserve daily quota.
    """
    api_key = await settings_service.get_setting(db, "mdblist_api_key")
    if not api_key:
        return

    result = await db.execute(
        select(Movie).where(
            or_(Movie.rt_score.is_(None), Movie.rt_score == 0)
        ).limit(limit)
    )
    movies = result.scalars().all()
    if not movies:
        logger.info("backfill_rt_scores: nothing to fetch")
        return

    logger.info("backfill_rt_scores: fetching RT scores for %d movies", len(movies))
    fetched = 0
    async with httpx.AsyncClient(timeout=10.0) as client:
        for movie in movies:
            ok = await _fetch_and_store_rt(movie, client, api_key)
            if not ok:
                break
            fetched += 1
            await asyncio.sleep(0.1)  # ~10 req/s — well within MDBList free tier

    logger.info("backfill_rt_scores: %d/%d processed", fetched, len(movies))
