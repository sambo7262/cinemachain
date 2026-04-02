"""Search endpoints — movie title search and person name search.

QMODE-01: GET /search/movies?q=  — enriched movie title search
QMODE-02: GET /search/actors?q=  — person name -> TMDB credits -> movie list
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.models import Movie, WatchEvent
from app.services.mdblist import fetch_rt_scores
from app.services.tmdb import TMDBClient

# Import private helper from game.py — no circular dependency:
# search.py -> game.py (game.py does NOT import from search.py)
from app.routers.game import _ensure_movie_details_in_db, _fetch_mpaa_rating

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/search", tags=["search"])


def _movie_to_dto(movie: Movie, watched_ids: set) -> dict:
    """Convert a Movie ORM row to EligibleMovieDTO-compatible dict."""
    return {
        "tmdb_id": movie.tmdb_id,
        "title": movie.title,
        "year": movie.year,
        "poster_path": movie.poster_path,
        "vote_average": movie.vote_average,
        "genres": movie.genres,  # JSON string e.g. '["Action","Drama"]' or None
        "runtime": movie.runtime,
        "watched": movie.tmdb_id in watched_ids,
        "selectable": True,
        "via_actor_name": None,
        "vote_count": movie.vote_count,
        "mpaa_rating": movie.mpaa_rating,
        "overview": movie.overview,
        "rt_score": movie.rt_score if movie.rt_score and movie.rt_score > 0 else None,
        "rt_audience_score": movie.rt_audience_score if movie.rt_audience_score and movie.rt_audience_score > 0 else None,
        "imdb_id": movie.imdb_id if movie.imdb_id else None,
        "imdb_rating": movie.imdb_rating if movie.imdb_rating and movie.imdb_rating > 0 else None,
        "metacritic_score": movie.metacritic_score if movie.metacritic_score and movie.metacritic_score > 0 else None,
        "letterboxd_score": movie.letterboxd_score if movie.letterboxd_score and movie.letterboxd_score > 0 else None,
        "mdb_avg_score": movie.mdb_avg_score if movie.mdb_avg_score and movie.mdb_avg_score > 0 else None,
    }


async def _watched_set(db: AsyncSession) -> set:
    """Return set of all watched tmdb_ids from WatchEvent table."""
    rows = await db.execute(select(WatchEvent.tmdb_id))
    return {r[0] for r in rows.all()}


@router.get("/movies")
async def search_movies_enriched(
    q: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """QMODE-01: Search TMDB by title, upsert stubs, enrich details + RT, return full movie list."""
    tmdb: TMDBClient = request.app.state.tmdb_client

    # 1. Search TMDB
    async with tmdb._sem:
        r = await tmdb._client.get("/search/movie", params={"query": q})
    r.raise_for_status()
    raw_results = r.json().get("results", [])[:20]

    if not raw_results:
        return []

    # 2. Upsert movie stubs
    for m in raw_results:
        year = int(m["release_date"][:4]) if m.get("release_date") else None
        stmt = pg_insert(Movie).values(
            tmdb_id=m["id"],
            title=m.get("title", ""),
            year=year,
            poster_path=m.get("poster_path"),
            vote_average=m.get("vote_average"),
            vote_count=m.get("vote_count"),
        ).on_conflict_do_update(
            index_elements=["tmdb_id"],
            set_={
                "title": m.get("title", ""),
                "poster_path": m.get("poster_path"),
                "vote_average": m.get("vote_average"),
                "vote_count": m.get("vote_count"),
            },
        )
        await db.execute(stmt)
    await db.commit()

    tmdb_ids = [m["id"] for m in raw_results]

    # 3. Enrich: fetch runtime, genres, overview for stubs missing genre data
    await _ensure_movie_details_in_db(tmdb_ids, tmdb, db)

    # 3b. Enrich: fetch MPAA rating for movies where mpaa_rating IS NULL (never fetched)
    mpaa_rows = await db.execute(
        select(Movie.tmdb_id).where(
            Movie.tmdb_id.in_(tmdb_ids),
            Movie.mpaa_rating.is_(None),
        )
    )
    for (mid,) in mpaa_rows.all():
        await _fetch_mpaa_rating(mid, tmdb, db)

    # 4. Enrich: fetch RT scores where rt_score IS NULL
    await fetch_rt_scores(tmdb_ids, db)
    await db.commit()

    # 5. Load enriched rows
    result = await db.execute(select(Movie).where(Movie.tmdb_id.in_(tmdb_ids)))
    movies = {m.tmdb_id: m for m in result.scalars().all()}

    watched_ids = await _watched_set(db)

    return [
        _movie_to_dto(movies[tid], watched_ids)
        for tid in tmdb_ids
        if tid in movies
    ]


@router.get("/actors")
async def search_actors(
    q: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """QMODE-02: Resolve person name -> top TMDB result -> combined cast+crew credits as movie list."""
    tmdb: TMDBClient = request.app.state.tmdb_client

    # 1. Resolve person name to TMDB person ID
    person = await tmdb.search_person(q)
    if not person:
        return []

    person_id = person["id"]

    # 2. Fetch movie credits (cast + crew)
    credits_data = await tmdb.fetch_actor_credits(person_id)
    cast = credits_data.get("cast", [])
    crew = credits_data.get("crew", [])

    # 3. Combine and deduplicate by tmdb_id
    seen: set = set()
    all_credits: list = []
    for entry in cast + crew:
        if entry.get("id") and entry["id"] not in seen:
            seen.add(entry["id"])
            all_credits.append(entry)

    if not all_credits:
        return []

    # 4. Upsert movie stubs
    for credit in all_credits:
        year = int(credit["release_date"][:4]) if credit.get("release_date") else None
        stmt = pg_insert(Movie).values(
            tmdb_id=credit["id"],
            title=credit.get("title", ""),
            year=year,
            poster_path=credit.get("poster_path"),
            vote_average=credit.get("vote_average"),
            vote_count=credit.get("vote_count"),
        ).on_conflict_do_update(
            index_elements=["tmdb_id"],
            set_={
                "title": credit.get("title", ""),
                "poster_path": credit.get("poster_path"),
                "vote_average": credit.get("vote_average"),
            },
        )
        await db.execute(stmt)
    await db.commit()

    tmdb_ids = [c["id"] for c in all_credits]

    # 5. Enrich details + RT (same pattern as search_movies_enriched)
    await _ensure_movie_details_in_db(tmdb_ids, tmdb, db)

    # 5b. Enrich: fetch MPAA rating for movies where mpaa_rating IS NULL (never fetched)
    mpaa_rows = await db.execute(
        select(Movie.tmdb_id).where(
            Movie.tmdb_id.in_(tmdb_ids),
            Movie.mpaa_rating.is_(None),
        )
    )
    for (mid,) in mpaa_rows.all():
        await _fetch_mpaa_rating(mid, tmdb, db)

    await fetch_rt_scores(tmdb_ids, db)
    await db.commit()

    # 6. Load enriched rows
    result = await db.execute(select(Movie).where(Movie.tmdb_id.in_(tmdb_ids)))
    movies = {m.tmdb_id: m for m in result.scalars().all()}

    watched_ids = await _watched_set(db)

    return [
        _movie_to_dto(movies[tid], watched_ids)
        for tid in tmdb_ids
        if tid in movies
    ]
