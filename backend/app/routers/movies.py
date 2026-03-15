import json
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.models import Actor, Credit, Movie, WatchEvent

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
