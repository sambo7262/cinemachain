from __future__ import annotations

import io
import csv
from datetime import datetime as _datetime
from pydantic import BaseModel
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from sqlalchemy import func as _func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.orm import selectinload

from app.db import engine, get_db
from app.models import Actor, Credit, GameSession, GameSessionStep, Movie, WatchEvent
from app.services.radarr import RadarrClient
from app.services.tmdb import TMDBClient

# Background-task DB session factory (separate from request-scoped sessions)
_bg_session_factory = async_sessionmaker(engine, expire_on_commit=False)

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
    watched_at: _datetime | None = None   # NEW — joined from WatchEvent at query time

    model_config = {"from_attributes": True}


class GameSessionResponse(BaseModel):
    id: int
    name: str = ""                         # NEW
    status: str
    current_movie_tmdb_id: int
    current_movie_watched: bool = False
    steps: list[StepResponse]
    radarr_status: str | None = None
    current_movie_title: str | None = None    # NEW — title of current movie from Movie table

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------

class CreateSessionRequest(BaseModel):
    start_movie_tmdb_id: int
    name: str                              # NEW — required


class CSVRow(BaseModel):
    movieName: str
    actorName: str
    order: int


class ImportCSVRequest(BaseModel):
    rows: list[CSVRow]
    name: str = "Imported Chain"           # NEW — optional with default


class PickActorRequest(BaseModel):
    actor_tmdb_id: int
    actor_name: str


class RequestMovieRequest(BaseModel):
    movie_tmdb_id: int
    movie_title: str


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


async def _enrich_steps_watched_at(
    steps: list[GameSessionStep], db: AsyncSession
) -> dict[int, _datetime]:
    """Return mapping of movie_tmdb_id -> watched_at for movies in the given steps.

    Uses MAX(watched_at) GROUP BY tmdb_id to guarantee at most one result per movie,
    even if multiple WatchEvent rows exist for the same tmdb_id.
    """
    tmdb_ids = [s.movie_tmdb_id for s in steps]
    if not tmdb_ids:
        return {}
    result = await db.execute(
        select(WatchEvent.tmdb_id, _func.max(WatchEvent.watched_at).label("watched_at"))
        .where(WatchEvent.tmdb_id.in_(tmdb_ids))
        .group_by(WatchEvent.tmdb_id)
    )
    return {row.tmdb_id: row.watched_at for row in result.all()}


def _build_session_response(
    session: GameSession,
    watched_at_map: dict[int, _datetime] | None = None,
    radarr_status: str | None = None,
    current_movie_title: str | None = None,    # NEW parameter
) -> GameSessionResponse:
    """Build GameSessionResponse with watched_at enrichment on each step."""
    steps = []
    for s in session.steps:
        wa = (watched_at_map or {}).get(s.movie_tmdb_id)
        steps.append(StepResponse(
            step_order=s.step_order,
            movie_tmdb_id=s.movie_tmdb_id,
            movie_title=s.movie_title,
            actor_tmdb_id=s.actor_tmdb_id,
            actor_name=s.actor_name,
            watched_at=wa,
        ))
    return GameSessionResponse(
        id=session.id,
        name=session.name,
        status=session.status,
        current_movie_tmdb_id=session.current_movie_tmdb_id,
        current_movie_watched=session.current_movie_watched,
        steps=steps,
        radarr_status=radarr_status,
        current_movie_title=current_movie_title,    # NEW
    )


def _resolve_current_movie_title(session: GameSession) -> str | None:
    """Derive current movie title from session steps (no extra DB query needed).

    Looks for the step whose movie_tmdb_id matches current_movie_tmdb_id.
    Falls back to the last step's title if no exact match (edge case during transitions).
    """
    for step in session.steps:
        if step.movie_tmdb_id == session.current_movie_tmdb_id:
            return step.movie_title
    # Fallback: last step by step_order
    if session.steps:
        last = max(session.steps, key=lambda s: s.step_order)
        return last.movie_title
    return None


async def _ensure_actor_credits_in_db(
    actor_tmdb_id: int,
    tmdb: TMDBClient,
    db: AsyncSession,
) -> None:
    """Fetch actor filmography from TMDB and upsert Movie + Credit rows.

    Called before eligible-movies DB query to ensure on-demand filmography is populated.
    Uses on_conflict_do_nothing so repeated calls are safe (idempotent).
    """
    try:
        data = await tmdb.fetch_actor_credits(actor_tmdb_id)
    except Exception:
        # TMDB unavailable — proceed with whatever is already cached
        return

    # Upsert actor row
    try:
        person = await tmdb.fetch_person(actor_tmdb_id)
    except Exception:
        person = {"name": f"Actor {actor_tmdb_id}", "profile_path": None}

    actor_stmt = pg_insert(Actor).values(
        tmdb_id=actor_tmdb_id,
        name=person.get("name", f"Actor {actor_tmdb_id}"),
        profile_path=person.get("profile_path"),
    ).on_conflict_do_nothing(index_elements=["tmdb_id"])
    await db.execute(actor_stmt)
    await db.commit()

    # Re-fetch actor to get its PK
    actor_result = await db.execute(select(Actor).where(Actor.tmdb_id == actor_tmdb_id))
    actor = actor_result.scalar_one_or_none()
    if actor is None:
        return

    # Upsert movie stubs from filmography
    for credit_data in data.get("cast", []):
        movie_stmt = pg_insert(Movie).values(
            tmdb_id=credit_data["id"],
            title=credit_data.get("title", ""),
            year=int(credit_data["release_date"][:4]) if credit_data.get("release_date") else None,
            poster_path=credit_data.get("poster_path"),
            vote_average=credit_data.get("vote_average"),
            genres=None,
        ).on_conflict_do_nothing(index_elements=["tmdb_id"])
        await db.execute(movie_stmt)
    await db.commit()

    # Upsert Credit rows linking actor to each movie
    for credit_data in data.get("cast", []):
        movie_result = await db.execute(
            select(Movie).where(Movie.tmdb_id == credit_data["id"])
        )
        movie = movie_result.scalar_one_or_none()
        if movie:
            credit_stmt = pg_insert(Credit).values(
                movie_id=movie.id,
                actor_id=actor.id,
                character=credit_data.get("character"),
                order=None,
            ).on_conflict_do_nothing(index_elements=["movie_id", "actor_id"])
            await db.execute(credit_stmt)
    await db.commit()


async def _prefetch_credits_background(
    movie_tmdb_id: int,
    tmdb: TMDBClient,
) -> None:
    """Background task: fetch cast of starting movie from TMDB, then populate credits for each cast member.

    Creates its own DB session (cannot share the request-scoped session after response is sent).
    Errors are swallowed — this is best-effort pre-population; eligible-movies falls back to on-demand fetch.
    """
    try:
        r = await tmdb._client.get(f"/movie/{movie_tmdb_id}/credits")
        r.raise_for_status()
        cast = r.json().get("cast", [])[:20]  # limit to top 20 billed actors
        async with _bg_session_factory() as db:
            for member in cast:
                actor_tmdb_id = member.get("id")
                if actor_tmdb_id:
                    await _ensure_actor_credits_in_db(actor_tmdb_id, tmdb, db)
    except Exception:
        # Best-effort — never crash background task
        pass


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
    # Check name uniqueness among active sessions
    name_check = await db.execute(
        select(GameSession)
        .where(GameSession.name == body.name)
        .where(GameSession.status.not_in(["archived", "ended"]))
    )
    if name_check.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Session name already in use")

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
        name=body.name,
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
    wa_map = await _enrich_steps_watched_at(session.steps, db)
    return _build_session_response(session, wa_map, current_movie_title=_resolve_current_movie_title(session))


@router.post("/sessions", status_code=201, response_model=GameSessionResponse)
async def create_session(
    body: CreateSessionRequest,
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Create a new active game session. Returns 409 if session name already in use."""
    # Check name uniqueness among active sessions (partial unique index enforces at DB level too)
    name_check = await db.execute(
        select(GameSession)
        .where(GameSession.name == body.name)
        .where(GameSession.status.not_in(["archived", "ended"]))
    )
    if name_check.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Session name already in use")

    # Look up movie title from DB if available
    movie_result = await db.execute(
        select(Movie).where(Movie.tmdb_id == body.start_movie_tmdb_id)
    )
    movie = movie_result.scalar_one_or_none()
    movie_title = movie.title if movie else None

    session = GameSession(
        status="active",
        current_movie_tmdb_id=body.start_movie_tmdb_id,
        name=body.name,
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

    # Fire Radarr check for starting movie (inline — result must be in response)
    radarr: RadarrClient = request.app.state.radarr_client
    try:
        radarr_result = await _request_radarr(body.start_movie_tmdb_id, radarr)
        radarr_status = radarr_result["status"]
    except Exception:
        radarr_status = "error"

    # Spawn background credits pre-fetch for starting movie cast
    tmdb: TMDBClient = request.app.state.tmdb_client
    background_tasks.add_task(_prefetch_credits_background, body.start_movie_tmdb_id, tmdb)

    wa_map = await _enrich_steps_watched_at(session.steps, db)
    response = _build_session_response(session, wa_map, radarr_status, current_movie_title=_resolve_current_movie_title(session))
    return response


@router.get("/sessions", response_model=list[GameSessionResponse])
async def list_sessions(
    include_archived: bool = Query(default=False),
    db: AsyncSession = Depends(get_db),
):
    """Return all active (non-ended, non-archived) sessions. Pass include_archived=true for all."""
    stmt = select(GameSession).options(selectinload(GameSession.steps))
    if include_archived:
        stmt = stmt.where(GameSession.status != "ended")
    else:
        stmt = stmt.where(GameSession.status.not_in(["ended", "archived"]))
    result = await db.execute(stmt)
    sessions = result.scalars().all()
    out = []
    for s in sessions:
        wa_map = await _enrich_steps_watched_at(s.steps, db)
        out.append(_build_session_response(s, wa_map, current_movie_title=_resolve_current_movie_title(s)))
    return out


@router.get("/sessions/archived", response_model=list[GameSessionResponse])
async def list_archived_sessions(db: AsyncSession = Depends(get_db)):
    """Return all sessions with status='archived'."""
    result = await db.execute(
        select(GameSession)
        .where(GameSession.status == "archived")
        .options(selectinload(GameSession.steps))
    )
    sessions = result.scalars().all()
    out = []
    for s in sessions:
        wa_map = await _enrich_steps_watched_at(s.steps, db)
        out.append(_build_session_response(s, wa_map, current_movie_title=_resolve_current_movie_title(s)))
    return out


@router.get("/sessions/active", response_model=GameSessionResponse | None)
async def get_active_session(db: AsyncSession = Depends(get_db)):
    """Return the current active/paused/awaiting_continue session with steps, or null if none."""
    session = await _get_single_active_session(db)
    if session is None:
        return None
    wa_map = await _enrich_steps_watched_at(session.steps, db)
    return _build_session_response(session, wa_map, current_movie_title=_resolve_current_movie_title(session))


@router.get("/sessions/{session_id}", response_model=GameSessionResponse)
async def get_session_by_id(session_id: int, db: AsyncSession = Depends(get_db)):
    """Return a single session by ID with steps and watched_at enrichment.

    Used by GameSession.tsx which navigates to /game/:sessionId and needs to
    fetch that specific session — not just the single 'active' session.
    """
    result = await db.execute(
        select(GameSession)
        .where(GameSession.id == session_id)
        .options(selectinload(GameSession.steps))
    )
    session = result.scalar_one_or_none()
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    wa_map = await _enrich_steps_watched_at(session.steps, db)
    return _build_session_response(
        session, wa_map, current_movie_title=_resolve_current_movie_title(session)
    )


@router.get("/sessions/{session_id}/export-csv")
async def export_session_csv(session_id: int, db: AsyncSession = Depends(get_db)):
    """Export chain history as CSV with columns: order,movie_name,actor_name."""
    result = await db.execute(
        select(GameSession)
        .where(GameSession.id == session_id)
        .options(selectinload(GameSession.steps))
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["order", "movie_name", "actor_name"])
    for step in sorted(session.steps, key=lambda s: s.step_order):
        writer.writerow([step.step_order, step.movie_title or "", ""])
        if step.actor_name:
            writer.writerow([step.step_order, "", step.actor_name])

    output.seek(0)
    filename = f"chain-{session.name or session.id}.csv"
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


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
    wa_map = await _enrich_steps_watched_at(session.steps, db)
    return _build_session_response(session, wa_map, current_movie_title=_resolve_current_movie_title(session))


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
    session.current_movie_watched = False
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
    wa_map = await _enrich_steps_watched_at(session.steps, db)
    return _build_session_response(session, wa_map, current_movie_title=_resolve_current_movie_title(session))


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
    wa_map = await _enrich_steps_watched_at(session.steps, db)
    return _build_session_response(session, wa_map, current_movie_title=_resolve_current_movie_title(session))


@router.post("/sessions/{session_id}/archive", response_model=GameSessionResponse)
async def archive_session(session_id: int, db: AsyncSession = Depends(get_db)):
    """Soft-archive a session: sets status='archived', records archived_at."""
    result = await db.execute(
        select(GameSession)
        .where(GameSession.id == session_id)
        .options(selectinload(GameSession.steps))
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    session.status = "archived"
    session.archived_at = _datetime.utcnow()
    await db.commit()
    result = await db.execute(
        select(GameSession).where(GameSession.id == session.id)
        .options(selectinload(GameSession.steps))
    )
    session = result.scalar_one()
    wa_map = await _enrich_steps_watched_at(session.steps, db)
    return _build_session_response(session, wa_map, current_movie_title=_resolve_current_movie_title(session))


@router.post("/sessions/{session_id}/mark-current-watched", response_model=GameSessionResponse)
async def mark_current_watched(session_id: int, db: AsyncSession = Depends(get_db)):
    """Mark the session's current movie as watched (manual fallback for non-Plex-Pass setups).

    Sets current_movie_watched=True, creates a WatchEvent for the current movie,
    and sets session status to 'awaiting_continue' so the UI shows the Continue prompt.
    Only operates on active sessions.
    """
    result = await db.execute(
        select(GameSession)
        .where(GameSession.id == session_id)
        .options(selectinload(GameSession.steps))
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.status == "archived":
        raise HTTPException(status_code=422, detail="Session is archived")
    if session.status not in ("active",):
        raise HTTPException(status_code=422, detail="Can only mark watched on an active session")

    # Mark watched on session
    session.current_movie_watched = True

    # Upsert WatchEvent for current movie
    stmt = pg_insert(WatchEvent).values(
        tmdb_id=session.current_movie_tmdb_id,
        movie_id=None,
        source="manual",
        watched_at=_datetime.utcnow(),
    ).on_conflict_do_nothing(index_elements=["tmdb_id"])
    await db.execute(stmt)

    # Advance to awaiting_continue (mirrors _maybe_advance_session in plex.py)
    session.status = "awaiting_continue"
    await db.commit()

    # Re-fetch with steps
    result = await db.execute(
        select(GameSession)
        .where(GameSession.id == session.id)
        .options(selectinload(GameSession.steps))
    )
    session = result.scalar_one()
    wa_map = await _enrich_steps_watched_at(session.steps, db)
    return _build_session_response(session, wa_map, current_movie_title=_resolve_current_movie_title(session))


@router.post("/sessions/{session_id}/continue-chain", response_model=GameSessionResponse)
async def continue_chain(session_id: int, db: AsyncSession = Depends(get_db)):
    """Transition awaiting_continue -> active WITHOUT resetting current_movie_watched.

    This is the correct endpoint for the 'Continue the chain' button in the UI.
    It preserves current_movie_watched=True so the eligible actors and movies
    queries remain unlocked after the user clicks Continue.

    CRITICAL DIFFERENCE FROM resume_session:
    - resume_session: paused -> active, resets current_movie_watched=False (new movie iteration)
    - continue_chain: awaiting_continue -> active, keeps current_movie_watched=True (same movie, pick actor)
    """
    result = await db.execute(
        select(GameSession)
        .where(GameSession.id == session_id)
        .options(selectinload(GameSession.steps))
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.status == "archived":
        raise HTTPException(status_code=422, detail="Session is archived")
    if session.status != "awaiting_continue":
        raise HTTPException(
            status_code=422,
            detail=f"continue-chain requires awaiting_continue status, got {session.status!r}",
        )
    # Transition to active — do NOT touch current_movie_watched
    session.status = "active"
    await db.commit()

    # Re-fetch with steps
    result = await db.execute(
        select(GameSession)
        .where(GameSession.id == session.id)
        .options(selectinload(GameSession.steps))
    )
    session = result.scalar_one()
    wa_map = await _enrich_steps_watched_at(session.steps, db)
    return _build_session_response(session, wa_map, current_movie_title=_resolve_current_movie_title(session))


# ---------------------------------------------------------------------------
# Radarr helper
# ---------------------------------------------------------------------------

async def _request_radarr(tmdb_id: int, radarr: RadarrClient) -> dict:
    """Two-step Radarr add flow: check existence, then lookup + add."""
    if await radarr.movie_exists(tmdb_id):
        return {"status": "already_in_radarr"}
    movie_payload = await radarr.lookup_movie(tmdb_id)
    if not movie_payload:
        raise HTTPException(status_code=502, detail="Movie not found in Radarr lookup")
    movie_payload["monitored"] = True
    movie_payload["addOptions"] = {"searchForMovie": True}
    movie_payload["rootFolderPath"] = await radarr.get_root_folder()
    movie_payload["qualityProfileId"] = await radarr.get_quality_profile_id()
    await radarr.add_movie(movie_payload)
    return {"status": "queued"}


# ---------------------------------------------------------------------------
# Eligible actors endpoint
# ---------------------------------------------------------------------------

@router.get("/sessions/{session_id}/eligible-actors")
async def get_eligible_actors(
    session_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Return actors from the session's current movie, excluding already-picked actors."""
    result = await db.execute(
        select(GameSession)
        .where(GameSession.id == session_id)
        .options(selectinload(GameSession.steps))
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if session.status == "archived":
        raise HTTPException(status_code=422, detail="Session is archived")

    if not session.current_movie_watched:
        raise HTTPException(
            status_code=423,
            detail="Watch the current movie before viewing eligible actors",
        )

    # Collect already-picked actor tmdb_ids from steps
    picked_ids = [s.actor_tmdb_id for s in session.steps if s.actor_tmdb_id is not None]

    # SQL join: Credit -> Actor + Movie, filter by current movie
    stmt = (
        select(Actor, Credit)
        .join(Credit, Credit.actor_id == Actor.id)
        .join(Movie, Movie.id == Credit.movie_id)
        .where(Movie.tmdb_id == session.current_movie_tmdb_id)
    )
    if picked_ids:
        stmt = stmt.where(Actor.tmdb_id.not_in(picked_ids))

    rows = await db.execute(stmt)
    actors = []
    for actor, credit in rows.all():
        actors.append({
            "tmdb_id": actor.tmdb_id,
            "name": actor.name,
            "profile_path": actor.profile_path,
            "character": credit.character,
        })

    # On-demand fallback: if the background pre-fetch has not completed yet,
    # synchronously fetch the current movie's cast and populate credits so the
    # query returns the correct result. Mirrors the combined-view branch.
    if not actors:
        tmdb: TMDBClient = request.app.state.tmdb_client
        try:
            r = await tmdb._client.get(f"/movie/{session.current_movie_tmdb_id}/credits")
            r.raise_for_status()
            cast = r.json().get("cast", [])[:20]
            for member in cast:
                aid = member.get("id")
                if aid:
                    await _ensure_actor_credits_in_db(aid, tmdb, db)
        except Exception:
            pass  # Degrade gracefully — return empty list if TMDB unavailable

        # Re-run the same query now that credits may be populated
        rows2 = await db.execute(stmt)
        for actor, credit in rows2.all():
            actors.append({
                "tmdb_id": actor.tmdb_id,
                "name": actor.name,
                "profile_path": actor.profile_path,
                "character": credit.character,
            })

    return actors


# ---------------------------------------------------------------------------
# Eligible movies endpoint
# ---------------------------------------------------------------------------

@router.get("/sessions/{session_id}/eligible-movies")
async def get_eligible_movies(
    session_id: int,
    request: Request,
    actor_id: int | None = Query(default=None),
    sort: str | None = Query(default=None),
    all_movies: bool = Query(default=False),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """Return eligible movies for the current game session.

    - actor_id: filter to a specific actor's filmography
    - sort: 'rating' (desc vote_average), 'runtime' (asc), 'genre' (asc)
    - all_movies: if False (default), only return unwatched movies
    """
    result = await db.execute(
        select(GameSession)
        .where(GameSession.id == session_id)
        .options(selectinload(GameSession.steps))
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if not session.current_movie_watched:
        raise HTTPException(
            status_code=423,
            detail="Watch the current movie before viewing eligible movies",
        )

    # Watched state: fetch all watched tmdb_ids
    watched_result = await db.execute(select(WatchEvent.tmdb_id))
    watched_ids = {row[0] for row in watched_result.all()}

    movies_map: dict[int, dict] = {}  # tmdb_id -> movie dict

    if actor_id is not None:
        # Ensure actor filmography is in DB (fetch from TMDB on demand if missing)
        tmdb: TMDBClient = request.app.state.tmdb_client
        await _ensure_actor_credits_in_db(actor_id, tmdb, db)

        # Specific actor filmography
        stmt = (
            select(Movie, Credit, Actor)
            .join(Credit, Credit.movie_id == Movie.id)
            .join(Actor, Actor.id == Credit.actor_id)
            .where(Actor.tmdb_id == actor_id)
        )
        rows = await db.execute(stmt)
        for movie, credit, actor in rows.all():
            if movie.tmdb_id not in movies_map:
                movies_map[movie.tmdb_id] = {
                    "tmdb_id": movie.tmdb_id,
                    "title": movie.title,
                    "year": movie.year,
                    "poster_path": movie.poster_path,
                    "vote_average": movie.vote_average,
                    "genres": movie.genres,
                    "runtime": movie.runtime,
                    "watched": movie.tmdb_id in watched_ids,
                    "selectable": movie.tmdb_id not in watched_ids,
                    "via_actor_name": actor.name,
                }
    else:
        # Combined view: get eligible actors first, then their filmographies
        picked_ids = [s.actor_tmdb_id for s in session.steps if s.actor_tmdb_id is not None]

        actor_stmt = (
            select(Actor, Credit)
            .join(Credit, Credit.actor_id == Actor.id)
            .join(Movie, Movie.id == Credit.movie_id)
            .where(Movie.tmdb_id == session.current_movie_tmdb_id)
        )
        if picked_ids:
            actor_stmt = actor_stmt.where(Actor.tmdb_id.not_in(picked_ids))

        eligible_actor_rows = await db.execute(actor_stmt)
        eligible_actor_tmdb_ids = [actor.tmdb_id for actor, _ in eligible_actor_rows.all()]

        # Ensure filmography credits are in DB for each eligible actor.
        # Mirrors the actor_id-scoped branch — fetches from TMDB on demand if missing.
        tmdb: TMDBClient = request.app.state.tmdb_client
        for aid in eligible_actor_tmdb_ids:
            await _ensure_actor_credits_in_db(aid, tmdb, db)

        if eligible_actor_tmdb_ids:
            film_stmt = (
                select(Movie, Credit, Actor)
                .join(Credit, Credit.movie_id == Movie.id)
                .join(Actor, Actor.id == Credit.actor_id)
                .where(Actor.tmdb_id.in_(eligible_actor_tmdb_ids))
            )
            film_rows = await db.execute(film_stmt)
            for movie, credit, actor in film_rows.all():
                if movie.tmdb_id not in movies_map:
                    movies_map[movie.tmdb_id] = {
                        "tmdb_id": movie.tmdb_id,
                        "title": movie.title,
                        "year": movie.year,
                        "poster_path": movie.poster_path,
                        "vote_average": movie.vote_average,
                        "genres": movie.genres,
                        "runtime": movie.runtime,
                        "watched": movie.tmdb_id in watched_ids,
                        "selectable": movie.tmdb_id not in watched_ids,
                        "via_actor_name": actor.name,
                    }

    movies = list(movies_map.values())

    # Filter: default only unwatched
    if not all_movies:
        movies = [m for m in movies if not m["watched"]]

    # Sort
    if sort == "rating":
        movies.sort(key=lambda m: (m["vote_average"] is None, -(m["vote_average"] or 0)))
    elif sort == "runtime":
        movies.sort(key=lambda m: (m["runtime"] is None, m["runtime"] or 0))
    elif sort == "genre":
        movies.sort(key=lambda m: (
            m["genres"] is None or m["genres"] == "",
            m["genres"] or "",
        ))

    total = len(movies)
    offset = (page - 1) * page_size
    movies = movies[offset : offset + page_size]

    return {
        "items": movies,
        "total": total,
        "page": page,
        "page_size": page_size,
        "has_more": (offset + page_size) < total,
    }


# ---------------------------------------------------------------------------
# Pick actor endpoint
# ---------------------------------------------------------------------------

@router.post("/sessions/{session_id}/pick-actor", response_model=GameSessionResponse)
async def pick_actor(
    session_id: int,
    body: PickActorRequest,
    db: AsyncSession = Depends(get_db),
):
    """Record an actor pick, adding a new GameSessionStep. Returns 409 if actor already picked."""
    result = await db.execute(
        select(GameSession)
        .where(GameSession.id == session_id)
        .options(selectinload(GameSession.steps))
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if session.status == "archived":
        raise HTTPException(status_code=422, detail="Session is archived")

    picked_ids = [s.actor_tmdb_id for s in session.steps if s.actor_tmdb_id is not None]
    if body.actor_tmdb_id in picked_ids:
        raise HTTPException(status_code=409, detail="Actor already picked in this session")

    next_order = max((s.step_order for s in session.steps), default=-1) + 1
    new_step = GameSessionStep(
        session_id=session.id,
        step_order=next_order,
        movie_tmdb_id=session.current_movie_tmdb_id,
        actor_tmdb_id=body.actor_tmdb_id,
        actor_name=body.actor_name,
    )
    db.add(new_step)
    await db.commit()

    # Re-fetch with steps loaded
    result = await db.execute(
        select(GameSession)
        .where(GameSession.id == session_id)
        .options(selectinload(GameSession.steps))
    )
    session = result.scalar_one()
    wa_map = await _enrich_steps_watched_at(session.steps, db)
    return _build_session_response(session, wa_map, current_movie_title=_resolve_current_movie_title(session))


# ---------------------------------------------------------------------------
# Request movie endpoint
# ---------------------------------------------------------------------------

@router.post("/sessions/{session_id}/request-movie")
async def request_movie(
    session_id: int,
    body: RequestMovieRequest,
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Queue a movie via Radarr and advance the session's current movie."""
    result = await db.execute(
        select(GameSession)
        .where(GameSession.id == session_id)
        .options(selectinload(GameSession.steps))
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if session.status == "archived":
        raise HTTPException(status_code=422, detail="Session is archived")

    # Validate: only unwatched movies can be requested
    watched_result = await db.execute(
        select(WatchEvent).where(WatchEvent.tmdb_id == body.movie_tmdb_id)
    )
    if watched_result.scalar_one_or_none():
        raise HTTPException(
            status_code=422,
            detail="Movie is already watched; select an unwatched movie",
        )

    # Add step for the chosen movie
    next_order = max((s.step_order for s in session.steps), default=-1) + 1
    new_step = GameSessionStep(
        session_id=session.id,
        step_order=next_order,
        movie_tmdb_id=body.movie_tmdb_id,
        movie_title=body.movie_title,
        actor_tmdb_id=None,
        actor_name=None,
    )
    db.add(new_step)

    # Advance the session's current movie
    session.current_movie_tmdb_id = body.movie_tmdb_id
    session.current_movie_watched = False
    await db.commit()

    # Spawn background credits pre-fetch for the new movie's cast
    tmdb: TMDBClient = request.app.state.tmdb_client
    background_tasks.add_task(_prefetch_credits_background, body.movie_tmdb_id, tmdb)

    # Re-fetch with steps loaded
    result = await db.execute(
        select(GameSession)
        .where(GameSession.id == session_id)
        .options(selectinload(GameSession.steps))
    )
    session = result.scalar_one()

    # Trigger Radarr
    radarr: RadarrClient = request.app.state.radarr_client
    radarr_result = await _request_radarr(body.movie_tmdb_id, radarr)

    wa_map = await _enrich_steps_watched_at(session.steps, db)
    return {
        "status": radarr_result["status"],
        "session": _build_session_response(session, wa_map, current_movie_title=_resolve_current_movie_title(session)),
    }
