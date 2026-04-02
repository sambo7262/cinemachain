"""MDBList API client for fetching movie ratings."""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime
import httpx
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Movie
from app.services import settings_service
from app.utils.masking import scrub_traceback

logger = logging.getLogger(__name__)


MDBLIST_API_URL = "https://mdblist.com/api/"


async def test_mdblist_connection(api_key: str) -> dict:
    """Test MDBList API key validity. Returns {"ok": bool, "error": str|None, "warning": None}."""
    try:
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
            resp = await client.get("https://mdblist.com/api/user", params={"apikey": api_key})
            if resp.status_code == 200:
                return {"ok": True, "error": None, "warning": None}
            elif resp.status_code == 401:
                return {"ok": False, "error": "MDBList API key is invalid", "warning": None}
            else:
                return {"ok": False, "error": f"MDBList returned status {resp.status_code}", "warning": None}
    except httpx.ConnectError:
        return {"ok": False, "error": "Cannot reach mdblist.com — check your network connection", "warning": None}
    except httpx.TimeoutException:
        return {"ok": False, "error": "MDBList request timed out", "warning": None}


async def fetch_rt_scores(
    tmdb_ids: list[int],
    db: AsyncSession,
) -> None:
    """Fetch all MDBList rating sources for movies where any rating field is NULL.

    Fetches synchronously (one request per movie). Results are written
    directly to the Movie rows in the DB. Caller must commit.

    Extracts: rt_score (tomatometer), rt_audience_score, imdb_rating,
    metacritic_score, letterboxd_score, mdb_avg_score, and imdb_id.

    Does nothing if mdblist_api_key is not configured.
    """
    api_key = await settings_service.get_setting(db, "mdblist_api_key")
    if not api_key:
        return

    # Only fetch for movies that don't have scores yet
    result = await db.execute(
        select(Movie).where(
            Movie.tmdb_id.in_(tmdb_ids),
            or_(Movie.rt_score.is_(None), Movie.imdb_rating.is_(None)),
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
                    # Movie not in MDBList — store sentinels so we don't retry
                    movie.rt_score = 0
                    movie.rt_audience_score = 0
                    movie.imdb_rating = 0.0
                    movie.metacritic_score = 0
                    movie.letterboxd_score = 0.0
                    movie.mdb_avg_score = 0.0
                    movie.imdb_id = ""
                    movie.mdblist_fetched_at = datetime.utcnow()
                    continue

                data = resp.json()
                ratings = data.get("ratings", [])

                tomatometer = None
                audience = None
                metacritic = None
                letterboxd = None
                imdb_val = None
                for r in ratings:
                    src = r.get("source", "")
                    if src in ("tomatoes", "tomatometr"):
                        tomatometer = r.get("value")
                    elif src in ("tomatoesaudience", "tomatoesau"):
                        audience = r.get("value")
                    elif src == "metacritic":
                        metacritic = r.get("value")
                    elif src == "letterboxd":
                        letterboxd = r.get("value")
                    elif src == "imdb":
                        imdb_val = r.get("value")

                imdbid = data.get("imdbid")
                score_average = data.get("score_average")

                if tomatometer is None and ratings:
                    sources = [r.get("source") for r in ratings]
                    logger.debug(
                        "MDBList tmdb_id=%d: no RT score found. Available sources: %s",
                        movie.tmdb_id, sources,
                    )

                # Store all fields. 0/0.0 sentinel means "fetched, no data available"
                # (distinguishes from None which means "never fetched").
                movie.imdb_id = imdbid  # string — None = never fetched, "" = not found
                movie.rt_score = tomatometer if tomatometer is not None else 0
                movie.rt_audience_score = audience if audience is not None else 0
                movie.imdb_rating = float(imdb_val) if imdb_val is not None else 0.0
                movie.metacritic_score = int(metacritic) if metacritic is not None else 0
                movie.letterboxd_score = float(letterboxd) if letterboxd is not None else 0.0
                movie.mdb_avg_score = float(score_average) if score_average is not None else 0.0
                movie.mdblist_fetched_at = datetime.utcnow()

            except Exception as exc:
                safe_tb = scrub_traceback(exc)
                logger.error(
                    "fetch_rt_scores: error for tmdb_id=%d\n%s",
                    movie.tmdb_id, safe_tb,
                )
                # Don't set fields — will retry next time
                continue


async def _fetch_and_store_rt(movie: Movie, client: httpx.AsyncClient, api_key: str) -> bool:
    """Fetch all MDBList rating fields for a single movie. Returns False if rate-limited (caller should stop)."""
    try:
        resp = await client.get(MDBLIST_API_URL, params={"apikey": api_key, "tm": movie.tmdb_id})
        if resp.status_code == 429:
            logger.warning("MDBList rate limited (429) — stopping nightly backfill")
            return False
        if resp.status_code == 404:
            movie.rt_score = 0
            movie.rt_audience_score = 0
            movie.imdb_rating = 0.0
            movie.metacritic_score = 0
            movie.letterboxd_score = 0.0
            movie.mdb_avg_score = 0.0
            movie.imdb_id = ""
            movie.mdblist_fetched_at = datetime.utcnow()
            return True
        if resp.status_code != 200:
            logger.warning("MDBList returned %d for tmdb_id=%d", resp.status_code, movie.tmdb_id)
            return True

        data = resp.json()
        ratings = data.get("ratings", [])
        tomatometer = None
        audience = None
        metacritic = None
        letterboxd = None
        imdb_val = None
        for r in ratings:
            src = r.get("source", "")
            if src in ("tomatoes", "tomatometr"):
                tomatometer = r.get("value")
            elif src in ("tomatoesaudience", "tomatoesau"):
                audience = r.get("value")
            elif src == "metacritic":
                metacritic = r.get("value")
            elif src == "letterboxd":
                letterboxd = r.get("value")
            elif src == "imdb":
                imdb_val = r.get("value")

        imdbid = data.get("imdbid")
        score_average = data.get("score_average")

        if tomatometer is None and ratings:
            logger.debug("MDBList tmdb_id=%d: no RT score. Sources: %s", movie.tmdb_id, [r.get("source") for r in ratings])

        movie.imdb_id = imdbid
        movie.rt_score = tomatometer if tomatometer is not None else 0
        movie.rt_audience_score = audience if audience is not None else 0
        movie.imdb_rating = float(imdb_val) if imdb_val is not None else 0.0
        movie.metacritic_score = int(metacritic) if metacritic is not None else 0
        movie.letterboxd_score = float(letterboxd) if letterboxd is not None else 0.0
        movie.mdb_avg_score = float(score_average) if score_average is not None else 0.0
        movie.mdblist_fetched_at = datetime.utcnow()
        return True
    except Exception as exc:
        safe_tb = scrub_traceback(exc)
        logger.error(
            "Failed to fetch MDBList scores for tmdb_id=%d\n%s",
            movie.tmdb_id, safe_tb,
        )
        return True  # don't stop the batch on network errors


async def backfill_mdblist_scores(db: AsyncSession, limit: int = 500) -> None:
    """Nightly pass: fetch all MDBList rating fields for movies missing any rating data.

    Unlike fetch_rt_scores (on-demand), this catches movies where any new field is NULL,
    ensuring the full set of rating sources gets populated for every movie.
    Stops immediately on 429 to preserve daily quota.
    """
    api_key = await settings_service.get_setting(db, "mdblist_api_key")
    if not api_key:
        return

    result = await db.execute(
        select(Movie).where(
            or_(Movie.rt_score.is_(None), Movie.imdb_rating.is_(None))
        ).limit(limit)
    )
    movies = result.scalars().all()
    if not movies:
        logger.info("backfill_mdblist_scores: nothing to fetch")
        return

    logger.info("backfill_mdblist_scores: fetching rating data for %d movies", len(movies))
    fetched = 0
    async with httpx.AsyncClient(timeout=10.0) as client:
        for movie in movies:
            ok = await _fetch_and_store_rt(movie, client, api_key)
            if not ok:
                break
            fetched += 1
            await asyncio.sleep(1.0)  # ~1 req/s — stay within free tier rate limits

    logger.info("backfill_mdblist_scores: %d/%d processed", fetched, len(movies))


# Backward-compat alias — callers using the old name continue to work
backfill_rt_scores = backfill_mdblist_scores
