from __future__ import annotations

from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db import get_db
from app.models import GameSession, GameSessionStep, Movie
from app.services.tmdb import TMDBClient

router = APIRouter(prefix="/game", tags=["game"])


# ---------------------------------------------------------------------------
# Pydantic response schemas
# ---------------------------------------------------------------------------

class StepResponse(BaseModel):
    step_order: int
    movie_tmdb_id: int
    movie_title: str | None
    actor_tmdb_id: int | None
    actor_name: str | None

    model_config = {"from_attributes": True}


class GameSessionResponse(BaseModel):
    id: int
    status: str
    current_movie_tmdb_id: int
    steps: list[StepResponse]

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------

class CreateSessionRequest(BaseModel):
    start_movie_tmdb_id: int


class CSVRow(BaseModel):
    movieName: str
    actorName: str
    order: int


class ImportCSVRequest(BaseModel):
    rows: list[CSVRow]


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

async def _get_single_active_session(db: AsyncSession) -> GameSession | None:
    """Return the one active/paused/awaiting_continue session, or None."""
    result = await db.execute(
        select(GameSession)
        .where(GameSession.status.in_(["active", "paused", "awaiting_continue"]))
        .options(selectinload(GameSession.steps))
    )
    return result.scalar_one_or_none()


async def _resolve_movie_tmdb_id(title: str, tmdb: TMDBClient) -> int | None:
    """Search TMDB for a movie by title; pick the result with the highest vote_count."""
    r = await tmdb._client.get("/search/movie", params={"query": title})
    results = r.json().get("results", [])
    if not results:
        return None
    return max(results, key=lambda m: m.get("vote_count", 0))["id"]


async def _resolve_actor_tmdb_id(name: str, tmdb: TMDBClient) -> int | None:
    """Search TMDB for a person by name; return first result (ranked by popularity)."""
    r = await tmdb._client.get("/search/person", params={"query": name})
    results = r.json().get("results", [])
    if not results:
        return None
    return results[0]["id"]


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/sessions/import-csv", status_code=201, response_model=GameSessionResponse)
async def import_csv_session(
    body: ImportCSVRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Create a session with pre-populated steps from CSV rows (resolves names via TMDB)."""
    existing = await _get_single_active_session(db)
    if existing:
        raise HTTPException(status_code=409, detail="Active session already exists")

    tmdb: TMDBClient = request.app.state.tmdb_client

    steps_data = []
    for row in body.rows:
        movie_id = await _resolve_movie_tmdb_id(row.movieName, tmdb)
        actor_id = await _resolve_actor_tmdb_id(row.actorName, tmdb)
        steps_data.append({
            "step_order": row.order,
            "movie_tmdb_id": movie_id,
            "movie_title": row.movieName,
            "actor_tmdb_id": actor_id,
            "actor_name": row.actorName,
        })

    # First row's movie becomes current_movie_tmdb_id
    first_movie_id = steps_data[0]["movie_tmdb_id"] if steps_data else None
    if first_movie_id is None:
        raise HTTPException(status_code=422, detail="Could not resolve first movie from TMDB")

    session = GameSession(
        status="active",
        current_movie_tmdb_id=first_movie_id,
    )
    db.add(session)
    await db.flush()

    for step_data in steps_data:
        step = GameSessionStep(
            session_id=session.id,
            step_order=step_data["step_order"],
            movie_tmdb_id=step_data["movie_tmdb_id"],
            movie_title=step_data["movie_title"],
            actor_tmdb_id=step_data["actor_tmdb_id"],
            actor_name=step_data["actor_name"],
        )
        db.add(step)

    await db.commit()
    await db.refresh(session)

    # Re-fetch with steps loaded
    result = await db.execute(
        select(GameSession)
        .where(GameSession.id == session.id)
        .options(selectinload(GameSession.steps))
    )
    session = result.scalar_one()
    return GameSessionResponse.model_validate(session)


@router.post("/sessions", status_code=201, response_model=GameSessionResponse)
async def create_session(
    body: CreateSessionRequest,
    db: AsyncSession = Depends(get_db),
):
    """Create a new active game session. Returns 409 if an active/paused session already exists."""
    existing = await _get_single_active_session(db)
    if existing:
        raise HTTPException(status_code=409, detail="Active session already exists")

    # Look up movie title from DB if available
    movie_result = await db.execute(
        select(Movie).where(Movie.tmdb_id == body.start_movie_tmdb_id)
    )
    movie = movie_result.scalar_one_or_none()
    movie_title = movie.title if movie else None

    session = GameSession(
        status="active",
        current_movie_tmdb_id=body.start_movie_tmdb_id,
    )
    db.add(session)
    await db.flush()

    # Create initial step (step_order=0, no actor transition for starting movie)
    initial_step = GameSessionStep(
        session_id=session.id,
        step_order=0,
        movie_tmdb_id=body.start_movie_tmdb_id,
        movie_title=movie_title,
        actor_tmdb_id=None,
        actor_name=None,
    )
    db.add(initial_step)

    await db.commit()
    await db.refresh(session)

    # Re-fetch with steps loaded
    result = await db.execute(
        select(GameSession)
        .where(GameSession.id == session.id)
        .options(selectinload(GameSession.steps))
    )
    session = result.scalar_one()
    return GameSessionResponse.model_validate(session)


@router.get("/sessions/active", response_model=GameSessionResponse | None)
async def get_active_session(db: AsyncSession = Depends(get_db)):
    """Return the current active/paused/awaiting_continue session with steps, or null if none."""
    session = await _get_single_active_session(db)
    if session is None:
        return None
    return GameSessionResponse.model_validate(session)


@router.post("/sessions/{session_id}/pause", response_model=GameSessionResponse)
async def pause_session(session_id: int, db: AsyncSession = Depends(get_db)):
    """Set session status to paused."""
    result = await db.execute(
        select(GameSession)
        .where(GameSession.id == session_id)
        .options(selectinload(GameSession.steps))
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    session.status = "paused"
    await db.commit()
    await db.refresh(session)
    # Re-fetch with steps
    result = await db.execute(
        select(GameSession)
        .where(GameSession.id == session.id)
        .options(selectinload(GameSession.steps))
    )
    session = result.scalar_one()
    return GameSessionResponse.model_validate(session)


@router.post("/sessions/{session_id}/resume", response_model=GameSessionResponse)
async def resume_session(session_id: int, db: AsyncSession = Depends(get_db)):
    """Set session status to active and restore current_movie_tmdb_id to last step's movie."""
    result = await db.execute(
        select(GameSession)
        .where(GameSession.id == session_id)
        .options(selectinload(GameSession.steps))
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    session.status = "active"
    # Restore current movie to the last step's movie so eligible-actors panel is correct
    if session.steps:
        last_step = max(session.steps, key=lambda s: s.step_order)
        session.current_movie_tmdb_id = last_step.movie_tmdb_id
    await db.commit()
    # Re-fetch with steps
    result = await db.execute(
        select(GameSession)
        .where(GameSession.id == session.id)
        .options(selectinload(GameSession.steps))
    )
    session = result.scalar_one()
    return GameSessionResponse.model_validate(session)


@router.post("/sessions/{session_id}/end", response_model=GameSessionResponse)
async def end_session(session_id: int, db: AsyncSession = Depends(get_db)):
    """Set session status to ended."""
    result = await db.execute(
        select(GameSession)
        .where(GameSession.id == session_id)
        .options(selectinload(GameSession.steps))
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    session.status = "ended"
    await db.commit()
    # Re-fetch with steps
    result = await db.execute(
        select(GameSession)
        .where(GameSession.id == session.id)
        .options(selectinload(GameSession.steps))
    )
    session = result.scalar_one()
    return GameSessionResponse.model_validate(session)
