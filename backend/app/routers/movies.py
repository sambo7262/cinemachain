from __future__ import annotations

import json
from datetime import datetime

import sqlalchemy as sa
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.models import Actor, Credit, GlobalSave, Movie, WatchEvent
from app.services.tmdb import TMDBClient
from app.services.mdblist import fetch_rt_scores


class PosterWallItem(BaseModel):
    tmdb_id: int
    poster_path: str
    poster_local_path: str | None = None


class WatchedMovieDTO(BaseModel):
    tmdb_id: int
    title: str
    year: int | None = None
    poster_path: str | None = None
    vote_average: float | None = None
    genres: str | None = None          # raw JSON string, same as EligibleMovieDTO
    runtime: int | None = None
    mpaa_rating: str | None = None
    overview: str | None = None
    rt_score: int | None = None
    rt_audience_score: int | None = None
    imdb_id: str | None = None
    imdb_rating: float | None = None
    metacritic_score: int | None = None
    letterboxd_score: float | None = None
    mdb_avg_score: float | None = None
    watched_at: str                     # ISO 8601 datetime string
    personal_rating: int | None = None  # WatchEvent.rating


class WatchedMoviesResponse(BaseModel):
    items: list[WatchedMovieDTO]
    total: int
    page: int
    page_size: int
    has_more: bool


class RatingUpdate(BaseModel):
    rating: int | None = None  # None clears the rating


router = APIRouter(prefix="/movies", tags=["movies"])


@router.get("/search")
async def search_movies(
    q: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Search TMDB for movies by title. Returns lightweight list for lobby movie picker."""
    from app.services.tmdb import TMDBClient
    tmdb: TMDBClient = request.app.state.tmdb_client
    async with tmdb._sem:
        r = await tmdb._client.get("/search/movie", params={"query": q})
    r.raise_for_status()
    results = r.json().get("results", [])[:20]
    return [
        {
            "tmdb_id": m["id"],
            "title": m.get("title", ""),
            "year": int(m["release_date"][:4]) if m.get("release_date") else None,
            "poster_path": m.get("poster_path"),
        }
        for m in results
    ]


@router.get("/watched", response_model=WatchedMoviesResponse)
async def get_watched_movies(
    db: AsyncSession = Depends(get_db),
    sort: str = Query(default="title"),
    sort_dir: str = Query(default="asc"),
    search: str = Query(default=""),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=24, ge=1, le=100),
):
    """Return all watched movies with sort, search, and pagination.

    Sort keys: title, year, runtime, rating (TMDB vote_average), rt (RT score),
               watched_at, personal_rating.
    Nulls are always sorted last (null-stable two-pass pattern).
    """
    # Fetch all matching rows (join Movie + WatchEvent)
    stmt = (
        select(Movie, WatchEvent)
        .join(WatchEvent, WatchEvent.tmdb_id == Movie.tmdb_id)
    )
    if search:
        stmt = stmt.where(Movie.title.ilike(f"%{search}%"))

    result = await db.execute(stmt)
    rows = result.all()

    movies: list[dict] = []
    for movie, we in rows:
        movies.append({
            "tmdb_id": movie.tmdb_id,
            "title": movie.title or "",
            "year": movie.year,
            "poster_path": movie.poster_path,
            "vote_average": movie.vote_average,
            "genres": movie.genres,
            "runtime": movie.runtime,
            "mpaa_rating": movie.mpaa_rating,
            "overview": movie.overview,
            "rt_score": movie.rt_score,
            "rt_audience_score": movie.rt_audience_score,
            "imdb_id": movie.imdb_id,
            "imdb_rating": movie.imdb_rating,
            "metacritic_score": movie.metacritic_score,
            "letterboxd_score": movie.letterboxd_score,
            "mdb_avg_score": movie.mdb_avg_score,
            "watched_at": we.watched_at.isoformat() if we.watched_at else "",
            "personal_rating": we.rating,
        })

    # Null-stable two-pass sort
    _desc = sort_dir == "desc"

    if sort == "title":
        movies.sort(key=lambda m: (m["title"].lower(), m["tmdb_id"]), reverse=_desc)
    elif sort == "year":
        with_val = [m for m in movies if m.get("year") is not None]
        without_val = [m for m in movies if m.get("year") is None]
        with_val.sort(key=lambda m: (m["year"], m["tmdb_id"]), reverse=_desc)
        without_val.sort(key=lambda m: m["tmdb_id"])
        movies = with_val + without_val
    elif sort == "runtime":
        with_val = [m for m in movies if m.get("runtime") is not None]
        without_val = [m for m in movies if m.get("runtime") is None]
        with_val.sort(key=lambda m: (m["runtime"], m["tmdb_id"]), reverse=_desc)
        without_val.sort(key=lambda m: m["tmdb_id"])
        movies = with_val + without_val
    elif sort == "rating":
        with_val = [m for m in movies if m.get("vote_average") is not None]
        without_val = [m for m in movies if m.get("vote_average") is None]
        with_val.sort(key=lambda m: (m["vote_average"], m["tmdb_id"]), reverse=_desc)
        without_val.sort(key=lambda m: m["tmdb_id"])
        movies = with_val + without_val
    elif sort == "rt":
        with_val = [m for m in movies if m.get("rt_score") is not None]
        without_val = [m for m in movies if m.get("rt_score") is None]
        with_val.sort(key=lambda m: (m["rt_score"], m["tmdb_id"]), reverse=_desc)
        without_val.sort(key=lambda m: m["tmdb_id"])
        movies = with_val + without_val
    elif sort == "watched_at":
        with_val = [m for m in movies if m.get("watched_at")]
        without_val = [m for m in movies if not m.get("watched_at")]
        with_val.sort(key=lambda m: (m["watched_at"], m["tmdb_id"]), reverse=_desc)
        without_val.sort(key=lambda m: m["tmdb_id"])
        movies = with_val + without_val
    elif sort == "personal_rating":
        with_val = [m for m in movies if m.get("personal_rating") is not None]
        without_val = [m for m in movies if m.get("personal_rating") is None]
        with_val.sort(key=lambda m: (m["personal_rating"], m["tmdb_id"]), reverse=_desc)
        without_val.sort(key=lambda m: m["tmdb_id"])
        movies = with_val + without_val
    elif sort == "rt_audience":
        with_val = [m for m in movies if m.get("rt_audience_score") is not None]
        without_val = [m for m in movies if m.get("rt_audience_score") is None]
        with_val.sort(key=lambda m: (m["rt_audience_score"], m["tmdb_id"]), reverse=_desc)
        without_val.sort(key=lambda m: m["tmdb_id"])
        movies = with_val + without_val
    elif sort == "imdb":
        with_val = [m for m in movies if m.get("imdb_rating") is not None]
        without_val = [m for m in movies if m.get("imdb_rating") is None]
        with_val.sort(key=lambda m: (m["imdb_rating"], m["tmdb_id"]), reverse=_desc)
        without_val.sort(key=lambda m: m["tmdb_id"])
        movies = with_val + without_val
    elif sort == "metacritic":
        with_val = [m for m in movies if m.get("metacritic_score") is not None]
        without_val = [m for m in movies if m.get("metacritic_score") is None]
        with_val.sort(key=lambda m: (m["metacritic_score"], m["tmdb_id"]), reverse=_desc)
        without_val.sort(key=lambda m: m["tmdb_id"])
        movies = with_val + without_val
    elif sort == "letterboxd":
        with_val = [m for m in movies if m.get("letterboxd_score") is not None]
        without_val = [m for m in movies if m.get("letterboxd_score") is None]
        with_val.sort(key=lambda m: (m["letterboxd_score"], m["tmdb_id"]), reverse=_desc)
        without_val.sort(key=lambda m: m["tmdb_id"])
        movies = with_val + without_val
    elif sort == "mdb_avg":
        with_val = [m for m in movies if m.get("mdb_avg_score") is not None]
        without_val = [m for m in movies if m.get("mdb_avg_score") is None]
        with_val.sort(key=lambda m: (m["mdb_avg_score"], m["tmdb_id"]), reverse=_desc)
        without_val.sort(key=lambda m: m["tmdb_id"])
        movies = with_val + without_val
    else:
        # Unknown sort key: fall back to title asc
        movies.sort(key=lambda m: (m["title"].lower(), m["tmdb_id"]))

    total = len(movies)
    offset = (page - 1) * page_size
    paginated = movies[offset: offset + page_size]

    return WatchedMoviesResponse(
        items=[WatchedMovieDTO(**m) for m in paginated],
        total=total,
        page=page,
        page_size=page_size,
        has_more=(offset + page_size) < total,
    )


@router.get("/poster-wall", response_model=list[PosterWallItem])
async def get_poster_wall(
    limit: int = 40,
    db: AsyncSession = Depends(get_db),
):
    """Return poster URLs sourced from watched movies + popular movies supplement.

    Priority 1: Movies the user has watched (WatchEvent -> Movie join), filtered to
    those with poster_path IS NOT NULL.
    Priority 2: If fewer than 20 results, supplement from movies table ordered by
    vote_count DESC (popular movies already in DB cache), excluding already-collected IDs.
    Returns at most `limit` items.
    """
    # Step 1: collect from WatchEvents
    we_result = await db.execute(
        select(Movie.tmdb_id, Movie.poster_path, Movie.poster_local_path)
        .join(WatchEvent, WatchEvent.tmdb_id == Movie.tmdb_id)
        .where(Movie.poster_path.isnot(None))
        .order_by(Movie.tmdb_id)
        .limit(limit)
    )
    rows = we_result.all()
    collected = [
        PosterWallItem(tmdb_id=r[0], poster_path=r[1], poster_local_path=r[2])
        for r in rows
    ]

    # Step 2: supplement from any DB movies with a poster_path if fewer than 20 from watch history
    # Removed vote_count IS NOT NULL filter — on a fresh NAS the nightly cache may not have run,
    # so most movie stubs have vote_count=None. Order by vote_count DESC NULLS LAST so cached
    # popular movies appear first when available, with uncounted movies as fallback.
    if len(collected) < 20:
        already_ids = {item.tmdb_id for item in collected}
        needed = limit - len(collected)
        pop_result = await db.execute(
            select(Movie.tmdb_id, Movie.poster_path, Movie.poster_local_path)
            .where(
                Movie.poster_path.isnot(None),
                ~Movie.tmdb_id.in_(already_ids) if already_ids else sa.true(),
            )
            .order_by(Movie.vote_count.desc().nullslast(), Movie.tmdb_id)
            .limit(needed)
        )
        for r in pop_result.all():
            collected.append(
                PosterWallItem(tmdb_id=r[0], poster_path=r[1], poster_local_path=r[2])
            )

    return collected


TMDB_GENRE_IDS = {
    "Action": 28, "Adventure": 12, "Animation": 16, "Comedy": 35,
    "Crime": 80, "Documentary": 99, "Drama": 18, "Horror": 27,
    "Romance": 10749, "Science Fiction": 878, "Thriller": 53,
    "Fantasy": 14, "History": 36, "Music": 10402,
}


@router.get("/popular")
async def get_popular_by_genre(
    genre: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """QMODE-03: Return top ~100 popular movies for a genre via TMDB Discover (5 pages x 20)."""
    from app.routers.game import _ensure_movie_details_in_db
    tmdb: TMDBClient = request.app.state.tmdb_client

    # Fetch pages 1-5 sequentially (semaphore respected inside discover_movies)
    all_results: list = []
    seen_ids: set = set()
    for page in (1, 2, 3, 4, 5):
        data = await tmdb.discover_movies(genre, page=page)
        for m in data.get("results", []):
            if m.get("id") and m["id"] not in seen_ids:
                seen_ids.add(m["id"])
                all_results.append(m)

    if not all_results:
        return []

    # Upsert movie stubs
    for m in all_results:
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

    tmdb_ids = [m["id"] for m in all_results]

    # Enrich details (genres, runtime, overview) and RT scores
    await _ensure_movie_details_in_db(tmdb_ids, tmdb, db)
    await fetch_rt_scores(tmdb_ids, db)
    await db.commit()

    # Fetch enriched rows
    from sqlalchemy import select as _select
    result = await db.execute(_select(Movie).where(Movie.tmdb_id.in_(tmdb_ids)))
    movies = {m.tmdb_id: m for m in result.scalars().all()}

    # Fetch watched set
    watch_result = await db.execute(_select(WatchEvent.tmdb_id))
    watched_ids = {r[0] for r in watch_result.all()}

    return [
        {
            "tmdb_id": movies[tid].tmdb_id,
            "title": movies[tid].title,
            "year": movies[tid].year,
            "poster_path": movies[tid].poster_path,
            "vote_average": movies[tid].vote_average,
            "genres": movies[tid].genres,
            "runtime": movies[tid].runtime,
            "watched": tid in watched_ids,
            "selectable": True,
            "via_actor_name": None,
            "vote_count": movies[tid].vote_count,
            "mpaa_rating": movies[tid].mpaa_rating,
            "overview": movies[tid].overview,
            "rt_score": movies[tid].rt_score,
        }
        for tid in tmdb_ids
        if tid in movies
    ]


@router.post("/{tmdb_id}/request")
async def request_movie_standalone(
    tmdb_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """QMODE-06: Queue a movie via Radarr without a game session."""
    from app.services.radarr_helper import _request_radarr
    from app.services.radarr import RadarrClient
    radarr: RadarrClient = request.app.state.radarr_client
    result = await _request_radarr(tmdb_id, radarr)
    return result


@router.patch("/{tmdb_id}/rating")
async def set_movie_rating(
    tmdb_id: int,
    body: RatingUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Set or clear the personal rating on a WatchEvent. rating=null clears it."""
    result = await db.execute(
        select(WatchEvent).where(WatchEvent.tmdb_id == tmdb_id)
    )
    we = result.scalar_one_or_none()
    if we is None:
        raise HTTPException(status_code=404, detail="No watch event found for this movie")
    if body.rating is not None and not (1 <= body.rating <= 10):
        raise HTTPException(status_code=422, detail="Rating must be between 1 and 10")
    we.rating = body.rating
    await db.commit()
    return {"tmdb_id": tmdb_id, "rating": we.rating}


@router.post("/{tmdb_id}/save")
async def save_movie(
    tmdb_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Globally bookmark a movie. Surfaces as saved in any game session's eligible-movies list."""
    stmt = pg_insert(GlobalSave).values(
        tmdb_id=tmdb_id,
        saved_at=sa.func.now(),
    ).on_conflict_do_nothing(index_elements=["tmdb_id"])
    await db.execute(stmt)
    await db.commit()
    return {"tmdb_id": tmdb_id, "saved": True}


@router.delete("/{tmdb_id}/save")
async def unsave_movie(
    tmdb_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Remove a global bookmark."""
    await db.execute(
        sa.delete(GlobalSave).where(GlobalSave.tmdb_id == tmdb_id)
    )
    await db.commit()
    return {"tmdb_id": tmdb_id, "saved": False}


@router.get("/{tmdb_id}")
async def get_movie(tmdb_id: int, request: Request, db: AsyncSession = Depends(get_db)):
    """DATA-01 / DATA-03: Return movie details, fetching from TMDB on cache miss."""
    # Cache check
    result = await db.execute(
        select(Movie).where(Movie.tmdb_id == tmdb_id)
    )
    movie = result.scalar_one_or_none()

    if movie is None:
        # Cache miss — fetch from TMDB
        tmdb_client = request.app.state.tmdb_client
        try:
            data = await tmdb_client.fetch_movie(tmdb_id)
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"TMDB fetch failed: {exc}")

        movie = Movie(
            tmdb_id=data["id"],
            title=data["title"],
            year=int(data["release_date"][:4]) if data.get("release_date") else None,
            poster_path=data.get("poster_path"),  # raw path, e.g. "/abc.jpg"
            vote_average=data.get("vote_average"),
            genres=json.dumps([g["name"] for g in data.get("genres", [])]),
        )
        db.add(movie)
        await db.flush()  # get movie.id without committing

        # Upsert cast members and credits
        cast = data.get("credits", {}).get("cast", [])
        for cast_member in cast:
            actor_stmt = pg_insert(Actor).values(
                tmdb_id=cast_member["id"],
                name=cast_member["name"],
                profile_path=cast_member.get("profile_path"),
            ).on_conflict_do_nothing(index_elements=["tmdb_id"])
            await db.execute(actor_stmt)

            actor_result = await db.execute(
                select(Actor).where(Actor.tmdb_id == cast_member["id"])
            )
            actor = actor_result.scalar_one_or_none()
            if actor:
                credit_stmt = pg_insert(Credit).values(
                    movie_id=movie.id,
                    actor_id=actor.id,
                    character=cast_member.get("character"),
                    order=cast_member.get("order"),
                ).on_conflict_do_nothing(index_elements=["movie_id", "actor_id"])
                await db.execute(credit_stmt)

        await db.commit()
        await db.refresh(movie)

    # Check watch state
    we_result = await db.execute(
        select(WatchEvent).where(WatchEvent.tmdb_id == tmdb_id)
    )
    watch_event = we_result.scalar_one_or_none()

    return {
        "tmdb_id": movie.tmdb_id,
        "title": movie.title,
        "year": movie.year,
        "poster_path": movie.poster_path,
        "vote_average": movie.vote_average,
        "genres": json.loads(movie.genres) if movie.genres else [],
        "fetched_at": movie.fetched_at.isoformat() if movie.fetched_at else None,
        "watched": watch_event is not None,
    }


@router.patch("/{tmdb_id}/watched")
async def mark_movie_watched(
    tmdb_id: int,
    db: AsyncSession = Depends(get_db),
    source: str = "manual",
):
    """DATA-06: Log a WatchEvent for a movie. source param: 'manual' (default) | 'online' | 'radarr'."""
    if source not in ("manual", "online", "radarr"):
        source = "manual"
    stmt = pg_insert(WatchEvent).values(
        tmdb_id=tmdb_id,
        movie_id=None,
        source=source,
        watched_at=datetime.utcnow(),
    ).on_conflict_do_nothing(index_elements=["tmdb_id"])
    await db.execute(stmt)
    await db.commit()

    return {"tmdb_id": tmdb_id, "watched": True, "source": source}
