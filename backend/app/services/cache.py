from __future__ import annotations

import asyncio
import logging
import math
import os
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import select
from sqlalchemy import update as sa_update

from sqlalchemy import or_

from app.db import _bg_session_factory
from app.models import Movie
from app.routers.game import _ensure_actor_credits_in_db, _ensure_movie_cast_in_db, _ensure_movie_details_in_db
from app.services.mdblist import backfill_rt_scores
from app.services.tmdb import TMDBClient
from app.utils.masking import scrub_traceback

logger = logging.getLogger(__name__)


@dataclass
class _CacheState:
    running: bool = False
    last_run_at: datetime | None = None
    last_run_duration_s: float | None = None


_cache_state = _CacheState()


async def _download_posters_pass(tmdb: TMDBClient) -> None:
    """Download poster images for all movies that have poster_path but no local file yet.

    Stores posters at /static/posters/{tmdb_id}.jpg and updates Movie.poster_local_path
    to the URL-relative path /static/posters/{tmdb_id}.jpg.
    Uses TMDBClient._client (existing httpx.AsyncClient) to reuse connection pool.
    File writes use run_in_executor to avoid blocking the event loop.
    Rate limit: 0.05s sleep between downloads (same as TMDB 40 req/s convention).
    """
    dest_dir = "static/posters"
    os.makedirs(dest_dir, exist_ok=True)

    async with _bg_session_factory() as db:
        # Fetch all movies with poster_path set but no local file yet
        result = await db.execute(
            select(Movie.tmdb_id, Movie.poster_path)
            .where(
                Movie.poster_path.isnot(None),
                Movie.poster_local_path.is_(None),
            )
            .order_by(Movie.tmdb_id)
        )
        rows = result.all()

    logger.info("_download_posters_pass: %d posters to download", len(rows))
    downloaded = 0

    for tmdb_id, poster_path in rows:
        local_path = os.path.join(dest_dir, f"{tmdb_id}.jpg")
        url_path = f"/static/posters/{tmdb_id}.jpg"

        # Skip if file already exists on disk (race condition guard)
        if os.path.exists(local_path):
            # File exists but DB not updated — update DB and continue
            async with _bg_session_factory() as db:
                await db.execute(
                    sa_update(Movie)
                    .where(Movie.tmdb_id == tmdb_id)
                    .values(poster_local_path=url_path)
                )
                await db.commit()
            continue

        url = f"https://image.tmdb.org/t/p/w185{poster_path}"
        try:
            async with tmdb._sem:
                r = await tmdb._client.get(url, timeout=30)
            r.raise_for_status()
            content = r.content

            # Write file via executor to avoid blocking event loop
            loop = asyncio.get_event_loop()
            def _write(path: str, data: bytes) -> None:
                with open(path, "wb") as f:
                    f.write(data)
            await loop.run_in_executor(None, _write, local_path, content)

            # Update DB
            async with _bg_session_factory() as db:
                await db.execute(
                    sa_update(Movie)
                    .where(Movie.tmdb_id == tmdb_id)
                    .values(poster_local_path=url_path)
                )
                await db.commit()
            downloaded += 1
        except Exception as exc:
            logger.warning("poster download failed for tmdb_id=%d: %s", tmdb_id, exc)

        await asyncio.sleep(0.05)

    logger.info("_download_posters_pass: downloaded %d posters", downloaded)


async def _backfill_mpaa_pass(tmdb: TMDBClient, limit: int = 25000) -> None:
    """Fetch MPAA ratings for movies with NULL or empty mpaa_rating.

    Retries empty-string sentinel so previously-failed lookups get another chance.
    Uses 429 exponential backoff: starts at 5s, caps at 60s, skips after 3 retries.
    """
    async with _bg_session_factory() as db:
        result = await db.execute(
            select(Movie.tmdb_id).where(
                or_(Movie.mpaa_rating.is_(None), Movie.mpaa_rating == "")
            ).order_by(Movie.vote_count.desc().nulls_last()).limit(limit)
        )
        tmdb_ids = [row[0] for row in result.all()]

    logger.info("_backfill_mpaa_pass: %d movies need MPAA rating", len(tmdb_ids))
    fetched = 0
    for tmdb_id in tmdb_ids:
        try:
            async with tmdb._sem:
                r = await tmdb._client.get(f"/movie/{tmdb_id}/release_dates")

            if r.status_code == 429:
                retry_delay = 5.0
                for _attempt in range(3):
                    logger.warning("TMDB 429 on tmdb_id=%d, backing off %.0fs", tmdb_id, retry_delay)
                    await asyncio.sleep(retry_delay)
                    retry_delay = min(retry_delay * 2, 60.0)
                    async with tmdb._sem:
                        r = await tmdb._client.get(f"/movie/{tmdb_id}/release_dates")
                    if r.status_code != 429:
                        break
                if r.status_code == 429:
                    logger.error("TMDB 429 persistent for tmdb_id=%d, skipping", tmdb_id)
                    await asyncio.sleep(0.05)
                    continue

            r.raise_for_status()

            results = r.json().get("results", [])
            cert = ""
            for country in results:
                if country.get("iso_3166_1") == "US":
                    for rd in country.get("release_dates", []):
                        c = rd.get("certification", "")
                        if c:
                            cert = c
                            break
                    break

            async with _bg_session_factory() as db:
                await db.execute(
                    sa_update(Movie).where(Movie.tmdb_id == tmdb_id).values(mpaa_rating=cert)
                )
                await db.commit()
            if cert:
                fetched += 1
        except Exception as exc:
            logger.warning("_backfill_mpaa_pass: failed for tmdb_id=%d: %s", tmdb_id, exc)
        await asyncio.sleep(0.05)
    logger.info("_backfill_mpaa_pass: %d ratings found", fetched)


async def _backfill_rt_scores_pass(limit: int = 3000) -> None:
    """Fetch RT scores for movies with NULL or sentinel (0) rt_score."""
    async with _bg_session_factory() as db:
        await backfill_rt_scores(db, limit=limit)
        await db.commit()


async def _backfill_overview_pass(tmdb: TMDBClient, limit: int = 2000) -> None:
    """Fetch overview for movies with NULL overview from TMDB /movie/{id}."""
    async with _bg_session_factory() as db:
        result = await db.execute(
            select(Movie.tmdb_id).where(
                or_(Movie.overview.is_(None), Movie.overview == "")
            ).limit(limit)
        )
        tmdb_ids = [row[0] for row in result.all()]

    logger.info("_backfill_overview_pass: %d movies need overview", len(tmdb_ids))
    fetched = 0
    for tmdb_id in tmdb_ids:
        try:
            r = await tmdb._client.get(f"/movie/{tmdb_id}")
            r.raise_for_status()
            data = r.json()
            overview_val = data.get("overview") or None
            async with _bg_session_factory() as db:
                await db.execute(
                    sa_update(Movie)
                    .where(Movie.tmdb_id == tmdb_id)
                    .values(overview=overview_val)
                )
                await db.commit()
            if overview_val:
                fetched += 1
        except Exception as exc:
            logger.warning("overview backfill failed for tmdb_id=%d: %s", tmdb_id, exc)
        await asyncio.sleep(0.05)
    logger.info("_backfill_overview_pass: %d overviews fetched", fetched)


async def nightly_cache_job(tmdb: TMDBClient, top_n: int = 5000, top_actors: int = 1500) -> None:
    """Fetch top-N movies by vote count and ensure all are fully cached in the DB.

    Incremental: skips movies where fetched_at IS NOT NULL AND genres IS NOT NULL.
    Uses the shared TMDBClient (with existing _sem concurrency limit).
    """
    _cache_state.running = True
    start = datetime.utcnow()
    try:
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

                if r.status_code == 429:
                    retry_delay = 5.0
                    for _attempt in range(3):
                        logger.warning("TMDB 429 on discover page %d, backing off %.0fs", page, retry_delay)
                        await asyncio.sleep(retry_delay)
                        retry_delay = min(retry_delay * 2, 60.0)
                        r = await tmdb._client.get(
                            "/discover/movie",
                            params={
                                "sort_by": "vote_count.desc",
                                "vote_count.gte": 500,
                                "page": page,
                            },
                        )
                        if r.status_code != 429:
                            break
                    if r.status_code == 429:
                        logger.error("TMDB 429 persistent on discover page %d, stopping collect", page)
                        break

                r.raise_for_status()
            except Exception as exc:
                safe_tb = scrub_traceback(exc)
                logger.error("nightly_cache_job: TMDB discover failed on page %d\n%s", page, safe_tb)
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

        logger.info("nightly_cache_job: movie enrichment complete")

        # --- Movie stub backfill: enrich rows missing title or genres ---
        async with _bg_session_factory() as db:
            stub_result = await db.execute(
                select(Movie.tmdb_id).where(
                    (Movie.title == "") | Movie.genres.is_(None)
                ).order_by(
                    Movie.vote_count.desc().nulls_last()
                ).limit(25000)
            )
            stub_ids = [row[0] for row in stub_result.all()]
        logger.info("nightly_cache_job: %d movie stubs need backfill", len(stub_ids))

        if stub_ids:
            async with _bg_session_factory() as db:
                await _ensure_movie_details_in_db(stub_ids, tmdb, db)

        # --- MPAA backfill pass ---
        await _backfill_mpaa_pass(tmdb)

        # --- Poster download pass ---
        logger.info("nightly_cache_job: starting poster download pass")
        await _download_posters_pass(tmdb)

        # --- RT score backfill pass ---
        await _backfill_rt_scores_pass()

        # --- Actor pre-fetch pass: configurable top popular actors ---
        logger.info("nightly_cache_job: fetching top %d actors for pre-population", top_actors)
        actor_ids: list[int] = []
        actor_pages = math.ceil(top_actors / 20)
        for actor_page in range(1, actor_pages + 1):
            try:
                r = await tmdb._client.get("/person/popular", params={"page": actor_page})
                r.raise_for_status()
                for person in r.json().get("results", []):
                    actor_ids.append(person["id"])
                await asyncio.sleep(0.05)
            except Exception as exc:
                safe_tb = scrub_traceback(exc)
                logger.error("nightly_cache_job: actor page %d failed\n%s", actor_page, safe_tb)
                break

        logger.info("nightly_cache_job: pre-fetching credits for %d actors", len(actor_ids))
        async with _bg_session_factory() as db:
            for actor_id in actor_ids:
                try:
                    await _ensure_actor_credits_in_db(actor_id, tmdb, db)
                except Exception as exc:
                    logger.warning("nightly_cache_job: actor %d pre-fetch failed: %s", actor_id, exc)
                await asyncio.sleep(0.05)
        logger.info("nightly_cache_job: actor pre-fetch complete")

        logger.info("nightly_cache_job: complete")
    finally:
        _cache_state.running = False
        _cache_state.last_run_at = start
        _cache_state.last_run_duration_s = (datetime.utcnow() - start).total_seconds()
