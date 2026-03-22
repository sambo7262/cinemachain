from __future__ import annotations

import asyncio
import logging
import os

from sqlalchemy import select
from sqlalchemy import update as sa_update

from sqlalchemy import or_

from app.db import _bg_session_factory
from app.models import Movie
from app.routers.game import _ensure_actor_credits_in_db, _ensure_movie_cast_in_db, _ensure_movie_details_in_db, _fetch_mpaa_rating
from app.services.mdblist import backfill_rt_scores
from app.services.tmdb import TMDBClient

logger = logging.getLogger(__name__)


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


async def _backfill_mpaa_pass(tmdb: TMDBClient, limit: int = 2000) -> None:
    """Fetch MPAA ratings for movies with NULL or empty mpaa_rating.

    Retries empty-string sentinel so previously-failed lookups get another chance.
    """
    async with _bg_session_factory() as db:
        result = await db.execute(
            select(Movie.tmdb_id).where(
                or_(Movie.mpaa_rating.is_(None), Movie.mpaa_rating == "")
            ).limit(limit)
        )
        tmdb_ids = [row[0] for row in result.all()]

    logger.info("_backfill_mpaa_pass: %d movies need MPAA rating", len(tmdb_ids))
    fetched = 0
    for tmdb_id in tmdb_ids:
        async with _bg_session_factory() as db:
            cert = await _fetch_mpaa_rating(tmdb_id, tmdb, db)
            if cert:
                fetched += 1
        await asyncio.sleep(0.05)
    logger.info("_backfill_mpaa_pass: %d ratings found", fetched)


async def _backfill_rt_scores_pass(limit: int = 500) -> None:
    """Fetch RT scores for movies with NULL or sentinel (0) rt_score."""
    async with _bg_session_factory() as db:
        await backfill_rt_scores(db, limit=limit)
        await db.commit()


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

    logger.info("nightly_cache_job: movie enrichment complete")

    # --- Actor pre-fetch pass: top 1500 popular actors ---
    logger.info("nightly_cache_job: fetching top actors for pre-population")
    actor_ids: list[int] = []
    for actor_page in range(1, 76):  # 75 pages × 20 = 1500 actors
        try:
            r = await tmdb._client.get("/person/popular", params={"page": actor_page})
            r.raise_for_status()
            for person in r.json().get("results", []):
                actor_ids.append(person["id"])
            await asyncio.sleep(0.05)
        except Exception as exc:
            logger.error("nightly_cache_job: actor page %d failed: %s", actor_page, exc)
            break

    logger.info("nightly_cache_job: pre-fetching credits for %d actors", len(actor_ids))
    async with _bg_session_factory() as db:
        for actor_id in actor_ids:
            await _ensure_actor_credits_in_db(actor_id, tmdb, db)
            await asyncio.sleep(0.05)
    logger.info("nightly_cache_job: actor pre-fetch complete")

    # --- Movie stub backfill: enrich rows missing title or genres ---
    async with _bg_session_factory() as db:
        stub_result = await db.execute(
            select(Movie.tmdb_id).where(
                (Movie.title == "") | Movie.genres.is_(None)
            ).limit(2000)
        )
        stub_ids = [row[0] for row in stub_result.all()]
    logger.info("nightly_cache_job: %d movie stubs need backfill", len(stub_ids))

    if stub_ids:
        async with _bg_session_factory() as db:
            await _ensure_movie_details_in_db(stub_ids, tmdb, db)

    # --- Poster download pass ---
    logger.info("nightly_cache_job: starting poster download pass")
    await _download_posters_pass(tmdb)

    # --- MPAA backfill pass ---
    await _backfill_mpaa_pass(tmdb)

    # --- RT score backfill pass ---
    await _backfill_rt_scores_pass()

    logger.info("nightly_cache_job: complete")
