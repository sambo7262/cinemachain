import json

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db import get_db
from app.models import Actor, Credit, Movie, WatchEvent

router = APIRouter(prefix="/actors", tags=["actors"])


@router.get("/{tmdb_id}/filmography")
async def get_actor_filmography(tmdb_id: int, request: Request, db: AsyncSession = Depends(get_db)):
    """DATA-02 / DATA-03: Return actor details and filmography, fetching from TMDB on cache miss."""
    result = await db.execute(
        select(Actor).where(Actor.tmdb_id == tmdb_id)
    )
    actor = result.scalar_one_or_none()

    if actor is None:
        tmdb_client = request.app.state.tmdb_client
        try:
            data = await tmdb_client.fetch_actor_credits(tmdb_id)
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"TMDB fetch failed: {exc}")

        # fetch_actor_credits only returns movie credits, not the actor's own metadata.
        # Use fetch_person to get name and profile_path.
        try:
            person = await tmdb_client.fetch_person(tmdb_id)
        except Exception:
            person = {"name": f"Actor {tmdb_id}", "profile_path": None}

        actor_stmt = pg_insert(Actor).values(
            tmdb_id=tmdb_id,
            name=person.get("name", f"Actor {tmdb_id}"),
            profile_path=person.get("profile_path"),
        ).on_conflict_do_nothing(index_elements=["tmdb_id"])
        await db.execute(actor_stmt)
        await db.commit()

        result = await db.execute(select(Actor).where(Actor.tmdb_id == tmdb_id))
        actor = result.scalar_one_or_none()

        # Upsert movie stubs for each credit
        for credit_data in data.get("cast", []):
            movie_stmt = pg_insert(Movie).values(
                tmdb_id=credit_data["id"],
                title=credit_data.get("title", ""),
                year=int(credit_data["release_date"][:4]) if credit_data.get("release_date") else None,
                poster_path=credit_data.get("poster_path"),
                vote_average=credit_data.get("vote_average"),
                genres=None,  # genre_ids integers only from this endpoint; resolve on demand
            ).on_conflict_do_nothing(index_elements=["tmdb_id"])
            await db.execute(movie_stmt)

        await db.commit()

        # Create credit rows linking actor to each movie
        for credit_data in data.get("cast", []):
            movie_result = await db.execute(
                select(Movie).where(Movie.tmdb_id == credit_data["id"])
            )
            movie = movie_result.scalar_one_or_none()
            if movie and actor:
                credit_stmt = pg_insert(Credit).values(
                    movie_id=movie.id,
                    actor_id=actor.id,
                    character=credit_data.get("character"),
                    order=None,
                ).on_conflict_do_nothing(index_elements=["movie_id", "actor_id"])
                await db.execute(credit_stmt)

        await db.commit()

    # Load credits via explicit selectinload (lazy="raise" requires this)
    result = await db.execute(
        select(Actor)
        .where(Actor.tmdb_id == tmdb_id)
        .options(
            selectinload(Actor.credits).selectinload(Credit.movie)
        )
    )
    actor = result.scalar_one_or_none()
    if actor is None:
        raise HTTPException(status_code=404, detail="Actor not found")

    # Batch check watch state for all movies in filmography
    movie_tmdb_ids = [c.movie.tmdb_id for c in actor.credits]
    watched_set: set[int] = set()
    if movie_tmdb_ids:
        we_result = await db.execute(
            select(WatchEvent.tmdb_id).where(WatchEvent.tmdb_id.in_(movie_tmdb_ids))
        )
        watched_set = {row[0] for row in we_result.fetchall()}

    return {
        "tmdb_id": actor.tmdb_id,
        "name": actor.name,
        "profile_path": actor.profile_path,
        "credits": [
            {
                "tmdb_id": c.movie.tmdb_id,
                "title": c.movie.title,
                "year": c.movie.year,
                "poster_path": c.movie.poster_path,
                "character": c.character,
                "watched": c.movie.tmdb_id in watched_set,
            }
            for c in actor.credits
        ],
    }
