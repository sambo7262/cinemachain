import json
from datetime import datetime

import sqlalchemy as sa
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.models import Actor, Credit, Movie, WatchEvent


class PosterWallItem(BaseModel):
    tmdb_id: int
    poster_path: str
    poster_local_path: str | None = None

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


@router.get("/watched")
async def get_watched_movies(db: AsyncSession = Depends(get_db)):
    """Return all movies the user has watched (from WatchEvent table, joined with Movie)."""
    result = await db.execute(
        select(Movie)
        .join(WatchEvent, WatchEvent.tmdb_id == Movie.tmdb_id)
        .order_by(Movie.title)
    )
    movies = result.scalars().all()
    return [
        {
            "tmdb_id": m.tmdb_id,
            "title": m.title,
            "year": m.year,
            "poster_path": m.poster_path,
        }
        for m in movies
    ]


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

    # Step 2: supplement from popular DB movies if fewer than 20 from watch history
    if len(collected) < 20:
        already_ids = {item.tmdb_id for item in collected}
        needed = limit - len(collected)
        pop_result = await db.execute(
            select(Movie.tmdb_id, Movie.poster_path, Movie.poster_local_path)
            .where(
                Movie.poster_path.isnot(None),
                Movie.vote_count.isnot(None),
                ~Movie.tmdb_id.in_(already_ids) if already_ids else sa.true(),
            )
            .order_by(Movie.vote_count.desc())
            .limit(needed)
        )
        for r in pop_result.all():
            collected.append(
                PosterWallItem(tmdb_id=r[0], poster_path=r[1], poster_local_path=r[2])
            )

    return collected


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
async def mark_movie_watched(tmdb_id: int, db: AsyncSession = Depends(get_db)):
    """DATA-06: Manually mark a movie as watched (fallback without Plex Pass)."""
    stmt = pg_insert(WatchEvent).values(
        tmdb_id=tmdb_id,
        movie_id=None,
        source="manual",
        watched_at=datetime.utcnow(),
    ).on_conflict_do_nothing(index_elements=["tmdb_id"])
    await db.execute(stmt)
    await db.commit()
    return {"tmdb_id": tmdb_id, "watched": True, "source": "manual"}
