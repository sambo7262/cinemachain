"""MDBList backfill endpoints — on-demand rating data refresh."""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from datetime import date, datetime, timedelta

import httpx
from fastapi import APIRouter, BackgroundTasks, HTTPException
from sqlalchemy import select, or_, func, asc, desc, nulls_first

from app.db import _bg_session_factory
from app.models import Movie
from app.services import settings_service
from app.services.mdblist import MDBLIST_API_URL
from app.utils.masking import scrub_traceback

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/mdblist", tags=["mdblist"])


@dataclass
class _BackfillState:
    running: bool = False
    fetched: int = 0
    total: int = 0
    calls_used_today: int = 0
    daily_limit: int = 25_000


_state = _BackfillState()


async def _increment_quota(db) -> int:
    """Increment daily quota counter in app_settings. Returns new count."""
    today_str = date.today().isoformat()
    reset_date = await settings_service.get_setting(db, "mdblist_calls_reset_date")
    if reset_date != today_str:
        await settings_service.save_settings(db, {
            "mdblist_calls_today": "1",
            "mdblist_calls_reset_date": today_str,
        })
        return 1
    count_str = await settings_service.get_setting(db, "mdblist_calls_today") or "0"
    new_count = int(count_str) + 1
    await settings_service.save_settings(db, {"mdblist_calls_today": str(new_count)})
    return new_count


async def _run_backfill():
    """Background task: fetch all MDBList data for movies missing any rating field."""
    try:
        async with _bg_session_factory() as db:
            api_key = await settings_service.get_setting(db, "mdblist_api_key")
            if not api_key:
                logger.warning("Backfill aborted — no mdblist_api_key configured")
                return

            # Order by mdblist_fetched_at: NULL first (never fetched), then oldest.
            # This ensures each run processes the most stale movies first and
            # never re-touches recently updated records while stale ones remain.
            result = await db.execute(
                select(Movie).order_by(nulls_first(asc(Movie.mdblist_fetched_at)))
            )
            movies = result.scalars().all()
            _state.total = len(movies)
            _state.fetched = 0

            if not movies:
                logger.info("Backfill: nothing to fetch")
                return

            logger.info("Backfill: starting for %d movies", len(movies))
            async with httpx.AsyncClient(timeout=10.0) as client:
                for movie in movies:
                    # Check quota
                    if _state.calls_used_today >= _state.daily_limit:
                        logger.warning("Backfill stopped — daily quota reached (%d)", _state.daily_limit)
                        break

                    try:
                        resp = await client.get(
                            MDBLIST_API_URL,
                            params={"apikey": api_key, "tm": movie.tmdb_id},
                        )
                        if resp.status_code == 429:
                            logger.warning("Backfill rate limited (429) — waiting 60s before continuing")
                            await asyncio.sleep(60)
                            continue
                        if resp.status_code == 404:
                            movie.rt_score = 0
                            movie.rt_audience_score = 0
                            movie.imdb_rating = 0.0
                            movie.metacritic_score = 0
                            movie.letterboxd_score = 0.0
                            movie.mdb_avg_score = 0.0
                            movie.imdb_id = ""
                            movie.mdblist_fetched_at = datetime.utcnow()
                        elif resp.status_code == 200:
                            data = resp.json()
                            ratings = data.get("ratings", [])
                            imdbid = data.get("imdbid")
                            score_average = data.get("score_average")

                            tomatometer = audience = metacritic = letterboxd_val = imdb_val = None
                            for r in ratings:
                                src = r.get("source", "")
                                if src in ("tomatoes", "tomatometr"):
                                    tomatometer = r.get("value")
                                elif src in ("tomatoesaudience", "tomatoesau"):
                                    audience = r.get("value")
                                elif src == "metacritic":
                                    metacritic = r.get("value")
                                elif src == "letterboxd":
                                    letterboxd_val = r.get("value")
                                elif src == "imdb":
                                    imdb_val = r.get("value")

                            movie.imdb_id = imdbid
                            movie.rt_score = tomatometer if tomatometer is not None else 0
                            movie.rt_audience_score = audience if audience is not None else 0
                            movie.imdb_rating = float(imdb_val) if imdb_val is not None else 0.0
                            movie.metacritic_score = int(metacritic) if metacritic is not None else 0
                            movie.letterboxd_score = float(letterboxd_val) if letterboxd_val is not None else 0.0
                            movie.mdb_avg_score = float(score_average) if score_average is not None else 0.0
                            movie.mdblist_fetched_at = datetime.utcnow()
                        else:
                            logger.warning("Backfill: MDBList returned %d for tmdb_id=%d", resp.status_code, movie.tmdb_id)
                            continue  # skip — don't increment fetched

                        _state.fetched += 1
                        count = await _increment_quota(db)
                        _state.calls_used_today = count
                        await db.commit()

                    except Exception as exc:
                        safe_tb = scrub_traceback(exc)
                        logger.error("Backfill: error for tmdb_id=%d\n%s", movie.tmdb_id, safe_tb)
                        continue

                    await asyncio.sleep(1.0)  # ~1 req/s — stay within free tier rate limits

            logger.info("Backfill complete: %d/%d fetched", _state.fetched, _state.total)
    finally:
        _state.running = False


@router.post("/backfill/start")
async def start_backfill(background_tasks: BackgroundTasks):
    if _state.running:
        raise HTTPException(409, "Backfill already running")

    # Load current quota from DB before starting
    async with _bg_session_factory() as db:
        today_str = date.today().isoformat()
        reset_date = await settings_service.get_setting(db, "mdblist_calls_reset_date")
        if reset_date != today_str:
            _state.calls_used_today = 0
        else:
            count_str = await settings_service.get_setting(db, "mdblist_calls_today") or "0"
            _state.calls_used_today = int(count_str)

        # Count movies never fetched from MDBList (NULL = never fetched)
        count_result = await db.execute(
            select(func.count(Movie.id)).where(Movie.mdblist_fetched_at.is_(None))
        )
        total = count_result.scalar() or 0

    _state.running = True
    _state.fetched = 0
    _state.total = total
    background_tasks.add_task(_run_backfill)
    return {"started": True, "total": total}


@router.get("/backfill/status")
async def backfill_status():
    calls_used = _state.calls_used_today
    # When not running, load the actual count from DB (in-memory resets on server restart)
    if not _state.running:
        try:
            async with _bg_session_factory() as db:
                today_str = date.today().isoformat()
                reset_date = await settings_service.get_setting(db, "mdblist_calls_reset_date")
                if reset_date == today_str:
                    count_str = await settings_service.get_setting(db, "mdblist_calls_today") or "0"
                    calls_used = int(count_str)
                else:
                    calls_used = 0
        except Exception:
            pass  # fall back to in-memory value if DB unavailable
    return {
        "running": _state.running,
        "fetched": _state.fetched,
        "total": _state.total,
        "calls_used_today": calls_used,
        "daily_limit": _state.daily_limit,
    }


async def mdblist_nightly_job():
    """Scheduled MDBList backfill: fills never-fetched movies, refreshes stale ones.

    Respects daily quota. Skips movies fetched within the last N days (configurable).
    Priority: null fetched_at first (never fetched), then oldest-fetched, both sub-ordered
    by vote_count DESC NULLS LAST (most popular first).
    """
    logger.info("mdblist_nightly_job: starting")

    async with _bg_session_factory() as db:
        api_key = await settings_service.get_setting(db, "mdblist_api_key")
        if not api_key:
            logger.warning("mdblist_nightly_job: no mdblist_api_key configured, aborting")
            return

        # Init quota from DB
        today_str = datetime.utcnow().strftime("%Y-%m-%d")
        reset_str = await settings_service.get_setting(db, "mdblist_calls_reset_date")
        if reset_str != today_str:
            _state.calls_used_today = 0
        else:
            count_str = await settings_service.get_setting(db, "mdblist_calls_today") or "0"
            _state.calls_used_today = int(count_str)
        _state.daily_limit = 25000

        if _state.calls_used_today >= _state.daily_limit:
            logger.info(
                "mdblist_nightly_job: quota exhausted (%d/%d), skipping",
                _state.calls_used_today, _state.daily_limit,
            )
            return

        # Read refetch threshold
        refetch_str = await settings_service.get_setting(db, "mdblist_refetch_days") or "90"
        refetch_days = int(refetch_str)
        cutoff = datetime.utcnow() - timedelta(days=refetch_days)

        result = await db.execute(
            select(Movie).where(
                or_(
                    Movie.mdblist_fetched_at.is_(None),
                    Movie.mdblist_fetched_at < cutoff,
                )
            ).order_by(
                nulls_first(asc(Movie.mdblist_fetched_at)),
                desc(Movie.vote_count).nulls_last(),
            )
        )
        movies = result.scalars().all()

    total = len(movies)
    logger.info("mdblist_nightly_job: %d movies eligible for fetch/refresh", total)

    if not movies:
        logger.info("mdblist_nightly_job: nothing to fetch")
        return

    processed = 0
    async with httpx.AsyncClient(timeout=10.0) as client:
        async with _bg_session_factory() as db:
            for movie in movies:
                # Check quota before each call
                if _state.calls_used_today >= _state.daily_limit:
                    logger.warning(
                        "mdblist_nightly_job: quota reached (%d/%d), stopping",
                        _state.calls_used_today, _state.daily_limit,
                    )
                    break

                try:
                    resp = await client.get(
                        MDBLIST_API_URL,
                        params={"apikey": api_key, "tm": movie.tmdb_id},
                    )
                    if resp.status_code == 429:
                        logger.warning("mdblist_nightly_job: rate limited (429), waiting 60s")
                        await asyncio.sleep(60)
                        continue
                    if resp.status_code == 404:
                        movie.rt_score = 0
                        movie.rt_audience_score = 0
                        movie.imdb_rating = 0.0
                        movie.metacritic_score = 0
                        movie.letterboxd_score = 0.0
                        movie.mdb_avg_score = 0.0
                        movie.imdb_id = ""
                        movie.mdblist_fetched_at = datetime.utcnow()
                    elif resp.status_code == 200:
                        data = resp.json()
                        ratings = data.get("ratings", [])
                        imdbid = data.get("imdbid")
                        score_average = data.get("score_average")

                        tomatometer = audience = metacritic = letterboxd_val = imdb_val = None
                        for r in ratings:
                            src = r.get("source", "")
                            if src in ("tomatoes", "tomatometr"):
                                tomatometer = r.get("value")
                            elif src in ("tomatoesaudience", "tomatoesau"):
                                audience = r.get("value")
                            elif src == "metacritic":
                                metacritic = r.get("value")
                            elif src == "letterboxd":
                                letterboxd_val = r.get("value")
                            elif src == "imdb":
                                imdb_val = r.get("value")

                        movie.imdb_id = imdbid
                        movie.rt_score = tomatometer if tomatometer is not None else 0
                        movie.rt_audience_score = audience if audience is not None else 0
                        movie.imdb_rating = float(imdb_val) if imdb_val is not None else 0.0
                        movie.metacritic_score = int(metacritic) if metacritic is not None else 0
                        movie.letterboxd_score = float(letterboxd_val) if letterboxd_val is not None else 0.0
                        movie.mdb_avg_score = float(score_average) if score_average is not None else 0.0
                        movie.mdblist_fetched_at = datetime.utcnow()
                    else:
                        logger.warning(
                            "mdblist_nightly_job: MDBList returned %d for tmdb_id=%d",
                            resp.status_code, movie.tmdb_id,
                        )
                        await asyncio.sleep(1.0)
                        continue

                    count = await _increment_quota(db)
                    _state.calls_used_today = count
                    await db.commit()
                    processed += 1

                    if processed % 500 == 0:
                        logger.info(
                            "mdblist_nightly_job: progress %d/%d (quota used: %d)",
                            processed, total, _state.calls_used_today,
                        )

                except Exception as exc:
                    safe_tb = scrub_traceback(exc)
                    logger.error("mdblist_nightly_job: error for tmdb_id=%d\n%s", movie.tmdb_id, safe_tb)
                    await asyncio.sleep(1.0)
                    continue

                await asyncio.sleep(1.0)  # ~1 req/s — stay within free tier rate limits

    logger.info("mdblist_nightly_job: complete — %d/%d movies processed", processed, total)
