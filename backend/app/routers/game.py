from __future__ import annotations

import io
import csv
import json
import sqlalchemy as sa
from datetime import datetime as _datetime
from pydantic import BaseModel
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request
from fastapi.responses import JSONResponse, StreamingResponse
from sqlalchemy import func as _func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db import engine, get_db, _bg_session_factory
from app.models import Actor, Credit, GameSession, GameSessionStep, Movie, WatchEvent
from app.services.radarr import RadarrClient
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
    watched_at: _datetime | None = None   # joined from WatchEvent at query time
    poster_path: str | None = None        # NEW — from Movie.poster_path
    profile_path: str | None = None       # NEW — from Actor.profile_path

    model_config = {"from_attributes": True}


class GameSessionResponse(BaseModel):
    id: int
    name: str = ""
    status: str
    current_movie_tmdb_id: int
    current_movie_watched: bool = False
    steps: list[StepResponse]
    radarr_status: str | None = None
    current_movie_title: str | None = None    # title of current movie from Movie table
    watched_count: int = 0                    # NEW — count of watched movie steps
    watched_runtime_minutes: int = 0          # NEW — sum of runtime for watched movie steps
    step_count: int = 0          # count of steps where actor_tmdb_id IS NOT NULL (actor picks only)
    unique_actor_count: int = 0  # count of distinct actors used across all steps
    created_at: _datetime | None = None  # session creation timestamp

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------

class CreateSessionRequest(BaseModel):
    start_movie_tmdb_id: int
    name: str                              # NEW — required
    start_movie_title: str | None = None   # title from frontend (avoids DB lookup miss)


class CSVRow(BaseModel):
    movieName: str
    actorName: str
    order: int


class TMDBSuggestion(BaseModel):
    tmdb_id: int
    title: str
    year: int | None


class UnresolvedRow(BaseModel):
    row: int          # 0-based index into body.rows
    csv_title: str
    suggestions: list[TMDBSuggestion]


class CsvValidationResponse(BaseModel):
    status: str = "validation_required"
    resolved_count: int
    unresolved: list[UnresolvedRow]


class CsvOverride(BaseModel):
    row: int
    tmdb_id: int


class ImportCSVRequest(BaseModel):
    rows: list[CSVRow]
    name: str = "Imported Chain"           # NEW — optional with default
    overrides: list[CsvOverride] = []


class PickActorRequest(BaseModel):
    actor_tmdb_id: int
    actor_name: str


class RequestMovieRequest(BaseModel):
    movie_tmdb_id: int
    movie_title: str | None = None


class EligibleMovieResponse(BaseModel):
    tmdb_id: int
    title: str
    year: int | None = None
    poster_path: str | None = None
    vote_average: float | None = None
    genres: str | None = None
    runtime: int | None = None
    vote_count: int | None = None
    mpaa_rating: str | None = None
    via_actor_name: str | None = None
    watched: bool = False
    selectable: bool = True
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


async def _enrich_steps_thumbnails(
    steps: list[GameSessionStep], db: AsyncSession
) -> tuple[dict[int, str | None], dict[int, str | None]]:
    """Return (movie_tmdb_id->poster_path, actor_tmdb_id->profile_path) for chain history display."""
    movie_tmdb_ids = [s.movie_tmdb_id for s in steps]
    actor_tmdb_ids = [s.actor_tmdb_id for s in steps if s.actor_tmdb_id is not None]

    poster_map: dict[int, str | None] = {}
    profile_map: dict[int, str | None] = {}

    if movie_tmdb_ids:
        m_rows = await db.execute(
            select(Movie.tmdb_id, Movie.poster_path).where(Movie.tmdb_id.in_(movie_tmdb_ids))
        )
        poster_map = {row.tmdb_id: row.poster_path for row in m_rows.all()}

    if actor_tmdb_ids:
        a_rows = await db.execute(
            select(Actor.tmdb_id, Actor.profile_path).where(Actor.tmdb_id.in_(actor_tmdb_ids))
        )
        profile_map = {row.tmdb_id: row.profile_path for row in a_rows.all()}

    return poster_map, profile_map


async def _enrich_steps_runtime(
    steps: list[GameSessionStep], db: AsyncSession
) -> dict[int, int | None]:
    """Return movie_tmdb_id->runtime for all steps (for session counter calculation)."""
    movie_tmdb_ids = list({s.movie_tmdb_id for s in steps})
    if not movie_tmdb_ids:
        return {}
    rows = await db.execute(
        select(Movie.tmdb_id, Movie.runtime).where(Movie.tmdb_id.in_(movie_tmdb_ids))
    )
    return {row.tmdb_id: row.runtime for row in rows.all()}


async def _fetch_mpaa_rating(
    tmdb_id: int,
    tmdb: TMDBClient,
    db: AsyncSession,
) -> str:
    """Fetch MPAA (US certification) from TMDB /movie/{id}/release_dates and cache on Movie row.

    Returns the certification string (e.g. "PG-13", "R") or "" if no US cert found.
    Stores "" as the sentinel for "fetched, no cert" so re-fetch is never triggered again.
    Errors are swallowed — caller treats missing mpaa_rating as NR in the UI.
    """
    try:
        r = await tmdb._client.get(f"/movie/{tmdb_id}/release_dates")
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
        # Store cert (or "" for "checked, no US cert") — None means "never fetched"
        await db.execute(
            sa.update(Movie).where(Movie.tmdb_id == tmdb_id).values(mpaa_rating=cert)
        )
        await db.commit()
        return cert
    except Exception:
        return ""


def _build_session_response(
    session: GameSession,
    watched_at_map: dict[int, _datetime] | None = None,
    radarr_status: str | None = None,
    current_movie_title: str | None = None,
    poster_map: dict[int, str | None] | None = None,
    profile_map: dict[int, str | None] | None = None,
    runtime_map: dict[int, int | None] | None = None,
) -> GameSessionResponse:
    """Build GameSessionResponse with watched_at, thumbnail, and counter enrichment on each step."""
    steps = []
    watched_count = 0
    watched_runtime_minutes = 0
    for s in session.steps:
        wa = (watched_at_map or {}).get(s.movie_tmdb_id)
        steps.append(StepResponse(
            step_order=s.step_order,
            movie_tmdb_id=s.movie_tmdb_id,
            movie_title=s.movie_title,
            actor_tmdb_id=s.actor_tmdb_id,
            actor_name=s.actor_name,
            watched_at=wa,
            poster_path=(poster_map or {}).get(s.movie_tmdb_id),
            profile_path=(profile_map or {}).get(s.actor_tmdb_id) if s.actor_tmdb_id else None,
        ))
        # Accumulate counters: movie steps (actor_tmdb_id IS NULL) that are watched
        if s.actor_tmdb_id is None and wa is not None:
            watched_count += 1
            runtime = (runtime_map or {}).get(s.movie_tmdb_id)
            if runtime is not None:
                watched_runtime_minutes += runtime
    # Compute new Phase 4.2 stats
    step_count = sum(1 for s in session.steps if s.actor_tmdb_id is not None)
    unique_actor_count = len({s.actor_tmdb_id for s in session.steps if s.actor_tmdb_id is not None})
    return GameSessionResponse(
        id=session.id,
        name=session.name,
        status=session.status,
        current_movie_tmdb_id=session.current_movie_tmdb_id,
        current_movie_watched=session.current_movie_watched,
        steps=steps,
        radarr_status=radarr_status,
        current_movie_title=current_movie_title,
        watched_count=watched_count,
        watched_runtime_minutes=watched_runtime_minutes,
        step_count=step_count,
        unique_actor_count=unique_actor_count,
        created_at=session.created_at,
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
    Short-circuits if Credit rows already exist for this actor — avoids TMDB call.
    """
    existing = await db.execute(
        select(_func.count()).select_from(Credit)
        .join(Actor, Actor.id == Credit.actor_id)
        .where(Actor.tmdb_id == actor_tmdb_id)
    )
    if existing.scalar_one() > 0:
        # Also check for blank-title stubs — if any exist, fall through to backfill them
        blank = await db.execute(
            select(_func.count()).select_from(Movie)
            .join(Credit, Credit.movie_id == Movie.id)
            .join(Actor, Actor.id == Credit.actor_id)
            .where(Actor.tmdb_id == actor_tmdb_id, Movie.title == "")
        )
        if blank.scalar_one() == 0:
            return

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
        _year = int(credit_data["release_date"][:4]) if credit_data.get("release_date") else None
        movie_stmt = pg_insert(Movie).values(
            tmdb_id=credit_data["id"],
            title=credit_data.get("title", ""),
            year=_year,
            poster_path=credit_data.get("poster_path"),
            vote_average=credit_data.get("vote_average"),
            vote_count=credit_data.get("vote_count"),
            genres=None,
        ).on_conflict_do_update(
            index_elements=["tmdb_id"],
            set_={
                # Always refresh these fields — stubs inserted by _ensure_movie_cast_in_db
                # use title="" and year=None; backfill them here from actor-credits data.
                "title": credit_data.get("title", ""),
                "year": _year,
                "poster_path": credit_data.get("poster_path"),
                "vote_count": credit_data.get("vote_count"),
                "vote_average": credit_data.get("vote_average"),
            }
        )
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


async def _ensure_movie_cast_in_db(
    movie_tmdb_id: int,
    tmdb: "TMDBClient",
    db: AsyncSession,
    top_n: int = 20,
) -> None:
    """Fetch all credits for a movie in a SINGLE TMDB call and batch-insert into DB.

    Replaces the old per-actor loop in the get_eligible_actors on-demand fallback.
    One /movie/{id}/credits call vs 20 separate /person/{id}/movie_credits calls —
    eliminates TMDB rate-limit failures when the background pre-fetch has not completed.
    """
    try:
        r = await tmdb._client.get(f"/movie/{movie_tmdb_id}/credits")
        r.raise_for_status()
        cast = r.json().get("cast", [])[:top_n]
    except Exception:
        return  # Degrade gracefully — background pre-fetch will populate later

    # Ensure Movie record exists so Credit FK is satisfiable.
    # CSV-imported sessions create GameSessionSteps but never insert into movies table;
    # this upsert guarantees the FK target exists even on first call.
    await db.execute(
        pg_insert(Movie)
        .values(tmdb_id=movie_tmdb_id, title="", year=None, genres=None, fetched_at=_datetime.utcnow())
        .on_conflict_do_nothing(index_elements=["tmdb_id"])
    )
    await db.flush()

    # Resolve movie PK ONCE — same movie_tmdb_id for every cast member in this call.
    movie_row = await db.execute(select(Movie).where(Movie.tmdb_id == movie_tmdb_id))
    movie_obj = movie_row.scalar_one_or_none()
    if not movie_obj:
        return  # Should never happen after the upsert above; degrade gracefully.

    for member in cast:
        aid = member.get("id")
        aname = member.get("name")
        profile = member.get("profile_path")
        character = member.get("character", "")
        if not aid or not aname:
            continue

        # Upsert Actor
        await db.execute(
            pg_insert(Actor)
            .values(tmdb_id=aid, name=aname, profile_path=profile, fetched_at=_datetime.utcnow())
            .on_conflict_do_update(
                index_elements=["tmdb_id"],
                set_={"name": aname, "profile_path": profile},
            )
        )
        await db.flush()

        # Resolve actor PK
        actor_row = await db.execute(select(Actor).where(Actor.tmdb_id == aid))
        actor_obj = actor_row.scalar_one_or_none()
        if not actor_obj:
            continue

        # Upsert Credit
        await db.execute(
            pg_insert(Credit)
            .values(
                actor_id=actor_obj.id,
                movie_id=movie_obj.id,
                character=character[:255],
            )
            .on_conflict_do_nothing(index_elements=["movie_id", "actor_id"])
        )

    await db.commit()


async def _ensure_movie_details_in_db(
    tmdb_ids: list[int],
    tmdb: TMDBClient,
    db: AsyncSession,
) -> None:
    """Fetch full movie details (genres + runtime) for any movie stubs missing genre data.

    Movie stubs inserted by _ensure_actor_credits_in_db have genres=None and runtime=None
    because /person/{id}/movie_credits only returns genre_ids (integers) and no runtime.
    Full details require a separate GET /movie/{id} call. This helper fetches those details
    on-demand for movies in the provided tmdb_ids list where genres IS NULL.
    Errors are swallowed per-movie so a single TMDB failure degrades gracefully.
    """
    if not tmdb_ids:
        return

    rows = await db.execute(
        select(Movie.tmdb_id).where(
            Movie.tmdb_id.in_(tmdb_ids),
            Movie.genres.is_(None),
        )
    )
    needs_fetch = [row[0] for row in rows.all()]

    for tmdb_id in needs_fetch:
        try:
            data = await tmdb.fetch_movie(tmdb_id)
            genres_json = json.dumps([g["name"] for g in data.get("genres", [])])
            runtime_val = data.get("runtime")
            await db.execute(
                sa.update(Movie).where(Movie.tmdb_id == tmdb_id).values(
                    genres=genres_json,
                    runtime=runtime_val,
                )
            )
            await db.commit()
        except Exception:
            # Degrade gracefully — do not let a single TMDB failure block the page
            pass


async def _prefetch_credits_background(
    movie_tmdb_id: int,
    tmdb: TMDBClient,
) -> None:
    """Background task: populate Credits for the starting movie's cast in a single TMDB call.

    Uses _ensure_movie_cast_in_db (1 call to /movie/{id}/credits) instead of
    _ensure_actor_credits_in_db per actor (20 calls to /person/{id}/movie_credits).
    This eliminates TMDB rate-limit exhaustion for movies with large-filmography cast members.
    Actor filmographies are fetched on-demand when the user selects an actor.
    """
    try:
        async with _bg_session_factory() as db:
            await _ensure_movie_cast_in_db(movie_tmdb_id, tmdb, db)
    except Exception:
        pass


import re as _re


def _title_confidence(query: str, result_title: str) -> str:
    """Return 'high' for near-exact match, 'medium' for contains-match, 'low' otherwise."""
    q = query.lower().strip()
    t = result_title.lower().strip()
    if q == t:
        return "high"
    # Remove common parenthetical suffixes before comparing
    q_clean = _re.sub(r"\s*[\(\[].*?[\)\]]", "", q).strip()
    t_clean = _re.sub(r"\s*[\(\[].*?[\)\]]", "", t).strip()
    if q_clean == t_clean:
        return "high"
    if q_clean in t_clean or t_clean in q_clean:
        return "medium"
    return "low"


async def _resolve_movie_tmdb_id(
    title: str, tmdb: TMDBClient
) -> tuple[str, int | None, list[dict]]:
    """Search TMDB for a movie by title.

    Returns (confidence, best_tmdb_id_or_None, top3_suggestions).
    confidence: 'high' | 'medium' | 'low' | 'none'
    top3_suggestions: list of {tmdb_id, title, year} dicts
    """
    r = await tmdb._client.get("/search/movie", params={"query": title})
    results = r.json().get("results", [])
    if not results:
        return ("none", None, [])

    # Sort by vote_count descending (most popular first) then take top 3
    sorted_results = sorted(results, key=lambda m: m.get("vote_count", 0), reverse=True)
    top3 = sorted_results[:3]
    suggestions = [
        {
            "tmdb_id": m["id"],
            "title": m.get("title", ""),
            "year": int(m["release_date"][:4]) if m.get("release_date") else None,
        }
        for m in top3
    ]

    best = top3[0]
    confidence = _title_confidence(title, best.get("title", ""))
    return (confidence, best["id"], suggestions)


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

@router.post("/sessions/import-csv", status_code=201)
async def import_csv_session(
    body: ImportCSVRequest,
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Validate-first CSV import with fuzzy match resolution.

    Pass 1: resolve all rows via TMDB. If all high-confidence -> import immediately.
    If any rows are ambiguous or unresolvable -> return 200 + validation_required payload.
    Pass 2 (re-submission with body.overrides): skip TMDB for overridden rows, import directly.
    """
    # Check name uniqueness among active sessions
    name_check = await db.execute(
        select(GameSession)
        .where(GameSession.name == body.name)
        .where(GameSession.status.not_in(["archived", "ended"]))
    )
    if name_check.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Session name already in use")

    tmdb: TMDBClient = request.app.state.tmdb_client

    # Build override lookup: row index -> confirmed tmdb_id
    override_map: dict[int, int] = {o.row: o.tmdb_id for o in body.overrides}

    steps_data = []
    step_order = 0
    unresolved: list[dict] = []
    resolved_count = 0

    # Each CSV row has movie_name + actor_name on the same row.
    # Expand into: one movie-pick step + one actor-pick step per row.
    for i, row in enumerate(body.rows):
        if not row.movieName:
            continue  # skip actor-only rows from old-format CSVs

        if i in override_map:
            # Re-submission: use confirmed tmdb_id, skip TMDB lookup
            movie_id = override_map[i]
            confidence = "high"
            suggestions: list[dict] = []
        else:
            confidence, movie_id, suggestions = await _resolve_movie_tmdb_id(row.movieName, tmdb)

        if confidence in ("high", "medium") and movie_id is not None:
            resolved_count += 1
            steps_data.append({
                "step_order": step_order,
                "movie_tmdb_id": movie_id,
                "movie_title": row.movieName,
                "actor_tmdb_id": None,
                "actor_name": None,
            })
            step_order += 1
            if row.actorName:
                actor_id = await _resolve_actor_tmdb_id(row.actorName, tmdb)
                steps_data.append({
                    "step_order": step_order,
                    "movie_tmdb_id": movie_id,
                    "movie_title": row.movieName,
                    "actor_tmdb_id": actor_id,
                    "actor_name": row.actorName,
                })
                step_order += 1
        else:
            # Low confidence or zero results — flag for user review
            unresolved.append({
                "row": i,
                "csv_title": row.movieName,
                "suggestions": suggestions,
            })

    # If any rows need review, return validation_required (do NOT create session)
    if unresolved:
        return JSONResponse(
            status_code=200,
            content={
                "status": "validation_required",
                "resolved_count": resolved_count,
                "unresolved": unresolved,
            },
        )

    if not steps_data:
        raise HTTPException(status_code=422, detail="No valid rows found in CSV")

    # All rows resolved — create the session
    last_movie_id = next(
        s["movie_tmdb_id"] for s in reversed(steps_data) if s["actor_tmdb_id"] is None
    )

    session = GameSession(
        status="active",
        current_movie_tmdb_id=last_movie_id,
        current_movie_watched=False,  # last CSV row is in-progress, not yet watched
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

    # Create WatchEvent records for all prior movie steps (not the last in-progress movie).
    # This ensures session counters (watched_count, watched_runtime_minutes) reflect the
    # full imported chain history immediately — not zeros.
    # Identify "prior" movies: all movie-pick steps whose movie is NOT the current in-progress one.
    prior_movie_ids = list({
        s["movie_tmdb_id"]
        for s in steps_data
        if s["actor_tmdb_id"] is None  # movie-pick steps only
        and s["movie_tmdb_id"] != last_movie_id  # exclude current in-progress movie
    })
    if prior_movie_ids:
        now = _datetime.utcnow()
        for mid in prior_movie_ids:
            we_stmt = pg_insert(WatchEvent).values(
                tmdb_id=mid,
                source="csv_import",
                watched_at=now,
            ).on_conflict_do_nothing(index_elements=["tmdb_id"])
            await db.execute(we_stmt)
        await db.commit()

    # Spawn background credits pre-fetch for the last (in-progress) movie's cast.
    # Mirrors create_session — ensures eligible actors are populated without waiting
    # for the on-demand fallback, which requires a Movie record to already exist.
    background_tasks.add_task(_prefetch_credits_background, last_movie_id, tmdb)

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

    # Prefer title from request body (frontend always knows it); fall back to DB lookup
    if body.start_movie_title:
        movie_title = body.start_movie_title
    else:
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
    poster_map, profile_map = await _enrich_steps_thumbnails(session.steps, db)
    runtime_map = await _enrich_steps_runtime(session.steps, db)
    return _build_session_response(
        session, wa_map,
        current_movie_title=_resolve_current_movie_title(session),
        poster_map=poster_map, profile_map=profile_map, runtime_map=runtime_map,
    )


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
    poster_map, profile_map = await _enrich_steps_thumbnails(session.steps, db)
    runtime_map = await _enrich_steps_runtime(session.steps, db)
    return _build_session_response(
        session, wa_map,
        current_movie_title=_resolve_current_movie_title(session),
        poster_map=poster_map, profile_map=profile_map, runtime_map=runtime_map,
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

    sorted_steps = sorted(session.steps, key=lambda s: s.step_order)
    step_by_order = {s.step_order: s for s in sorted_steps}
    # Only movie-pick steps (actor_tmdb_id IS NULL) form the chain rows.
    # The actor that bridges to the next movie lives in the immediately following step.
    movie_steps = [s for s in sorted_steps if s.actor_tmdb_id is None]

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["order", "movie_name", "actor_name"])
    for i, step in enumerate(movie_steps, start=1):
        actor_step = step_by_order.get(step.step_order + 1)
        actor_name = actor_step.actor_name if actor_step and actor_step.actor_tmdb_id else ""
        writer.writerow([i, step.movie_title or "", actor_name])

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
    """Two-step Radarr add flow: check existence, then lookup + add.

    Returns a status dict rather than raising — the session is already committed
    by the time this is called, so a Radarr failure must not produce a 500.
    """
    try:
        if await radarr.movie_exists(tmdb_id):
            return {"status": "already_in_radarr"}
        movie_payload = await radarr.lookup_movie(tmdb_id)
        if not movie_payload:
            return {"status": "not_found_in_radarr"}
        movie_payload["monitored"] = True
        movie_payload["addOptions"] = {"searchForMovie": True}
        movie_payload["rootFolderPath"] = await radarr.get_root_folder()
        movie_payload["qualityProfileId"] = await radarr.get_quality_profile_id()
        await radarr.add_movie(movie_payload)
        return {"status": "queued"}
    except Exception as exc:
        import logging
        logging.getLogger(__name__).warning("Radarr request failed for tmdb_id=%s: %s", tmdb_id, exc)
        return {"status": "error"}


# ---------------------------------------------------------------------------
# Eligible actors endpoint
# ---------------------------------------------------------------------------

@router.get("/sessions/{session_id}/eligible-actors")
async def get_eligible_actors(
    session_id: int,
    request: Request,
    include_ineligible: bool = Query(default=False),
    db: AsyncSession = Depends(get_db),
):
    """Return actors from the session's current movie.

    When include_ineligible=False (default), excludes already-picked actors.
    When include_ineligible=True, returns all cast with an is_eligible flag.
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

    if not session.current_movie_watched:
        raise HTTPException(
            status_code=423,
            detail="Watch the current movie before viewing eligible actors",
        )

    # Collect already-picked actor tmdb_ids from steps
    picked_ids = [s.actor_tmdb_id for s in session.steps if s.actor_tmdb_id is not None]
    picked_set = set(picked_ids)

    # SQL join: Credit -> Actor + Movie, filter by current movie
    stmt = (
        select(Actor, Credit)
        .join(Credit, Credit.actor_id == Actor.id)
        .join(Movie, Movie.id == Credit.movie_id)
        .where(Movie.tmdb_id == session.current_movie_tmdb_id)
    )
    if picked_ids and not include_ineligible:
        stmt = stmt.where(Actor.tmdb_id.not_in(picked_ids))

    rows = await db.execute(stmt)
    actors = []
    for actor, credit in rows.all():
        actor_dict = {
            "tmdb_id": actor.tmdb_id,
            "name": actor.name,
            "profile_path": actor.profile_path,
            "character": credit.character,
        }
        if include_ineligible:
            actor_dict["is_eligible"] = actor.tmdb_id not in picked_set
        actors.append(actor_dict)

    # On-demand fallback: if the background pre-fetch has not completed yet,
    # synchronously fetch the current movie's cast and populate credits so the
    # query returns the correct result. Mirrors the combined-view branch.
    if not actors:
        tmdb: TMDBClient = request.app.state.tmdb_client
        await _ensure_movie_cast_in_db(session.current_movie_tmdb_id, tmdb, db)

        # Re-run with a FRESH statement after all inserts are committed.
        # Reusing the pre-built `stmt` may miss newly inserted rows due to
        # SQLAlchemy async session transaction boundary semantics.
        fresh_stmt = (
            select(Actor, Credit)
            .join(Credit, Credit.actor_id == Actor.id)
            .join(Movie, Movie.id == Credit.movie_id)
            .where(Movie.tmdb_id == session.current_movie_tmdb_id)
        )
        if picked_ids and not include_ineligible:
            fresh_stmt = fresh_stmt.where(Actor.tmdb_id.not_in(picked_ids))

        rows2 = await db.execute(fresh_stmt)
        for actor, credit in rows2.all():
            actor_dict = {
                "tmdb_id": actor.tmdb_id,
                "name": actor.name,
                "profile_path": actor.profile_path,
                "character": credit.character,
            }
            if include_ineligible:
                actor_dict["is_eligible"] = actor.tmdb_id not in picked_set
            actors.append(actor_dict)

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

    # Movies already in this session's chain — always ineligible regardless of WatchEvent
    session_movie_ids = [s.movie_tmdb_id for s in session.steps]
    chain_movie_ids = set(session_movie_ids)

    # Watched state: scoped to THIS session only
    # (movies watched in other sessions remain eligible here)
    watched_result = await db.execute(
        select(WatchEvent.tmdb_id).where(
            WatchEvent.tmdb_id.in_(session_movie_ids)
        )
    )
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
                    "vote_count": movie.vote_count,
                    "mpaa_rating": movie.mpaa_rating,
                    "genres": movie.genres,
                    "runtime": movie.runtime,
                    "watched": movie.tmdb_id in watched_ids,
                    "selectable": movie.tmdb_id not in watched_ids and movie.tmdb_id not in chain_movie_ids,
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
                        "vote_count": movie.vote_count,
                        "mpaa_rating": movie.mpaa_rating,
                        "genres": movie.genres,
                        "runtime": movie.runtime,
                        "watched": movie.tmdb_id in watched_ids,
                        "selectable": movie.tmdb_id not in watched_ids and movie.tmdb_id not in chain_movie_ids,
                        "via_actor_name": actor.name,
                    }

    # Actor-scoped path only: fetch genres+runtime stubs and MPAA ratings on demand.
    # Combined-view (actor_id is None) skips all TMDB enrichment — returns DB-cached
    # data immediately to avoid sequential HTTP calls that cause NAS 504 timeouts.
    if actor_id is not None and hasattr(request.app.state, "tmdb_client"):
        _tmdb2 = request.app.state.tmdb_client
        await _ensure_movie_details_in_db(list(movies_map.keys()), _tmdb2, db)
        # Refresh genre + runtime values in movies_map from DB after fetch
        refreshed = await db.execute(
            select(Movie.tmdb_id, Movie.genres, Movie.runtime)
            .where(Movie.tmdb_id.in_(list(movies_map.keys())))
        )
        for row in refreshed.all():
            if row.tmdb_id in movies_map:
                movies_map[row.tmdb_id]["genres"] = row.genres
                movies_map[row.tmdb_id]["runtime"] = row.runtime

        # Fetch mpaa_rating on-demand for movies where it has never been fetched (mpaa_rating is None)
        # Sequential fetch is acceptable — cold start only; subsequent requests use cached value.
        _tmdb = request.app.state.tmdb_client
        for mid, m in movies_map.items():
            if m.get("mpaa_rating") is None:
                cert = await _fetch_mpaa_rating(mid, _tmdb, db)
                m["mpaa_rating"] = cert

    movies = list(movies_map.values())

    # Filter: exclude chain movies always; default only unwatched
    movies = [m for m in movies if m["tmdb_id"] not in chain_movie_ids]
    if not all_movies:
        movies = [m for m in movies if not m["watched"]]

    VOTE_FLOOR = 500

    def _effective_rating(m: dict) -> float | None:
        if m.get("vote_count") is None or m["vote_count"] < VOTE_FLOOR:
            return None
        return m.get("vote_average")

    # Sort
    if sort == "rating":
        movies.sort(key=lambda m: (_effective_rating(m) is None, -(_effective_rating(m) or 0)))
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

    # Resolve current movie title from existing steps (for the actor-pick step record)
    current_title: str | None = None
    for s in session.steps:
        if s.movie_tmdb_id == session.current_movie_tmdb_id and s.movie_title:
            current_title = s.movie_title
            break

    next_order = max((s.step_order for s in session.steps), default=-1) + 1
    new_step = GameSessionStep(
        session_id=session.id,
        step_order=next_order,
        movie_tmdb_id=session.current_movie_tmdb_id,
        movie_title=current_title,
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

    # Validate: only movies not already watched in THIS session can be requested
    # (a movie watched in a different session must remain requestable here)
    session_movie_ids = [s.movie_tmdb_id for s in session.steps]
    if body.movie_tmdb_id in session_movie_ids:
        watched_result = await db.execute(
            select(WatchEvent).where(
                WatchEvent.tmdb_id == body.movie_tmdb_id,
                WatchEvent.tmdb_id.in_(session_movie_ids),
            )
        )
        if watched_result.scalar_one_or_none():
            raise HTTPException(
                status_code=422,
                detail="Movie is already watched in this session; select an unwatched movie",
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

    # Trigger Radarr — outer guard mirrors create_session; session is already committed
    # so a Radarr failure must never surface as a 500.
    radarr: RadarrClient = request.app.state.radarr_client
    try:
        radarr_result = await _request_radarr(body.movie_tmdb_id, radarr)
    except Exception:
        radarr_result = {"status": "error"}

    wa_map = await _enrich_steps_watched_at(session.steps, db)
    return {
        "status": radarr_result["status"],
        "session": _build_session_response(session, wa_map, current_movie_title=_resolve_current_movie_title(session)),
    }


@router.delete("/sessions/{session_id}/steps/last", response_model=GameSessionResponse)
async def delete_last_step(
    session_id: int,
    db: AsyncSession = Depends(get_db),
):
    """SESSION-01: Remove the most recent step and revert session to the previous movie.

    Blocked when only 1 step remains (the starting movie cannot be removed).
    No Radarr cancellation — the Radarr request stays in queue regardless.
    """
    session = await db.get(GameSession, session_id, options=[selectinload(GameSession.steps)])
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    steps = sorted(session.steps, key=lambda s: s.step_order)
    if len(steps) <= 1:
        raise HTTPException(
            status_code=400,
            detail="Cannot delete the starting movie step. At least one step must remain.",
        )

    last_step = steps[-1]
    await db.delete(last_step)

    # Revert session state to previous step
    prev_step = steps[-2]
    session.current_movie_tmdb_id = prev_step.movie_tmdb_id
    session.current_movie_watched = False  # revert to unwatched so home page CTA appears

    # If session was awaiting_continue, revert to active so it is playable again
    if session.status == "awaiting_continue":
        session.status = "active"

    await db.commit()

    # Re-fetch with steps for response building
    refreshed = await db.get(GameSession, session_id, options=[selectinload(GameSession.steps)])
    watched_at_map = await _enrich_steps_watched_at(refreshed.steps, db)
    poster_map, profile_map = await _enrich_steps_thumbnails(refreshed.steps, db)
    runtime_map = await _enrich_steps_runtime(refreshed.steps, db)
    return _build_session_response(
        refreshed,
        watched_at_map=watched_at_map,
        current_movie_title=_resolve_current_movie_title(refreshed),
        poster_map=poster_map,
        profile_map=profile_map,
        runtime_map=runtime_map,
    )


@router.delete("/sessions/{session_id}", status_code=204)
async def delete_archived_session(
    session_id: int,
    db: AsyncSession = Depends(get_db),
):
    """SESSION-02: Permanently remove an archived session and all its steps from the DB.

    Only permitted when session.status == 'archived'. Active/paused sessions are protected.
    """
    session = await db.get(GameSession, session_id, options=[selectinload(GameSession.steps)])
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    if session.status != "archived":
        raise HTTPException(
            status_code=403,
            detail="Only archived sessions can be deleted. Archive the session first.",
        )

    # Delete all steps first (foreign key safety)
    for step in session.steps:
        await db.delete(step)
    await db.flush()

    await db.delete(session)
    await db.commit()
    # 204 No Content — FastAPI returns empty body automatically


@router.get("/sessions/{session_id}/suggestions", response_model=list[EligibleMovieResponse])
async def get_suggestions(
    session_id: int,
    db: AsyncSession = Depends(get_db),
):
    """UX-09: Return top 5 movies reachable via currently eligible actors, ranked by genre affinity + TMDB rating.

    Algorithm:
    1. Get eligible actors (cast of current_movie_tmdb_id minus already-picked actors)
    2. For each eligible actor, get their Credits -> candidate movie tmdb_ids
    3. Exclude already-picked movie tmdb_ids from session steps
    4. Score by genre overlap with user watch history (WatchEvents + session steps joined to Movie.genres)
    5. 500 vote_count floor; tie-break by vote_average desc
    6. Return top 5
    """
    session = await db.get(GameSession, session_id, options=[selectinload(GameSession.steps)])
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    # Step 1: get already-picked actor IDs and movie IDs from session steps
    picked_actor_ids = {s.actor_tmdb_id for s in session.steps if s.actor_tmdb_id is not None}
    picked_movie_ids = {s.movie_tmdb_id for s in session.steps}

    # Step 2: get eligible actors (cast of current movie, excluding picked actors)
    eligible_actor_rows = await db.execute(
        select(Actor.tmdb_id, Actor.id)
        .join(Credit, Credit.actor_id == Actor.id)
        .join(Movie, Movie.id == Credit.movie_id)
        .where(
            Movie.tmdb_id == session.current_movie_tmdb_id,
            Actor.tmdb_id.notin_(picked_actor_ids),
        )
    )
    eligible_actors = eligible_actor_rows.all()

    # Step 3: get candidate movies reachable via eligible actors (only when eligible actors exist)
    candidates = []
    if eligible_actors:
        eligible_actor_db_ids = [row.id for row in eligible_actors]
        candidate_rows = await db.execute(
            select(Movie.tmdb_id, Movie.title, Movie.year, Movie.poster_path,
                   Movie.vote_average, Movie.genres, Movie.runtime, Movie.vote_count,
                   Movie.mpaa_rating, Actor.tmdb_id.label("actor_tmdb_id"), Actor.name.label("actor_name"))
            .join(Credit, Credit.movie_id == Movie.id)
            .join(Actor, Actor.id == Credit.actor_id)
            .where(
                Credit.actor_id.in_(eligible_actor_db_ids),
                Movie.tmdb_id.notin_(picked_movie_ids),
                Movie.vote_count >= 500,
            )
        )
        candidates = candidate_rows.all()
    # No early return — fall through to genre-affinity fallback when candidates is empty

    # Step 4: build genre affinity from WatchEvents joined to Movie
    watch_genres_rows = await db.execute(
        select(Movie.genres)
        .join(WatchEvent, WatchEvent.tmdb_id == Movie.tmdb_id)
        .where(Movie.genres.isnot(None))
    )
    genre_freq: dict[str, int] = {}
    for row in watch_genres_rows.all():
        try:
            for g in json.loads(row.genres or "[]"):
                genre_freq[g] = genre_freq.get(g, 0) + 1
        except Exception:
            pass

    # Add genres from session steps movies as well
    session_movie_genres = await db.execute(
        select(Movie.genres).where(
            Movie.tmdb_id.in_(picked_movie_ids),
            Movie.genres.isnot(None),
        )
    )
    for row in session_movie_genres.all():
        try:
            for g in json.loads(row.genres or "[]"):
                genre_freq[g] = genre_freq.get(g, 0) + 1
        except Exception:
            pass

    # Step 5: deduplicate candidates (same movie may be reachable via multiple actors — keep highest-scored)
    # Score = genre overlap score; tie-break by vote_average
    best: dict[int, dict] = {}  # tmdb_id -> best candidate dict
    for row in candidates:
        try:
            movie_genres = json.loads(row.genres or "[]")
        except Exception:
            movie_genres = []
        genre_score = sum(genre_freq.get(g, 0) for g in movie_genres)
        rating = row.vote_average or 0.0
        current = best.get(row.tmdb_id)
        if current is None or (genre_score, rating) > (current["genre_score"], current["rating"]):
            best[row.tmdb_id] = {
                "tmdb_id": row.tmdb_id,
                "title": row.title,
                "year": row.year,
                "poster_path": row.poster_path,
                "vote_average": row.vote_average,
                "genres": row.genres,
                "runtime": row.runtime,
                "vote_count": row.vote_count,
                "mpaa_rating": row.mpaa_rating,
                "via_actor_name": row.actor_name,
                "genre_score": genre_score,
                "rating": rating,
            }

    # Step 6: sort by (genre_score desc, vote_average desc), take top 5
    top5 = sorted(best.values(), key=lambda x: (x["genre_score"], x["rating"]), reverse=True)[:5]

    # Fallback: if <5 game-mechanic results, fill with top genre-affinity movies from full DB
    if len(top5) < 5:
        existing_ids = {m["tmdb_id"] for m in top5} | picked_movie_ids
        fallback_rows = await db.execute(
            select(Movie.tmdb_id, Movie.title, Movie.year, Movie.poster_path,
                   Movie.vote_average, Movie.genres, Movie.runtime, Movie.vote_count, Movie.mpaa_rating)
            .where(
                Movie.tmdb_id.notin_(existing_ids),
                Movie.vote_count >= 500,
                Movie.genres.isnot(None),
                Movie.title != "",
            )
        )
        fallback_scored = []
        for row in fallback_rows.all():
            try:
                movie_genres = json.loads(row.genres or "[]")
            except Exception:
                movie_genres = []
            genre_score = sum(genre_freq.get(g, 0) for g in movie_genres)
            fallback_scored.append({
                "tmdb_id": row.tmdb_id, "title": row.title, "year": row.year,
                "poster_path": row.poster_path, "vote_average": row.vote_average,
                "genres": row.genres, "runtime": row.runtime, "vote_count": row.vote_count,
                "mpaa_rating": row.mpaa_rating, "via_actor_name": None,
                "genre_score": genre_score, "rating": row.vote_average or 0.0,
            })
        fallback_scored.sort(key=lambda x: (x["genre_score"], x["rating"]), reverse=True)
        needed = 5 - len(top5)
        top5 = top5 + fallback_scored[:needed]

    # Session-scoped watched check
    session_watched_tmdb_ids = await db.execute(
        select(WatchEvent.tmdb_id).where(
            WatchEvent.tmdb_id.in_([m["tmdb_id"] for m in top5])
        )
    )
    watched_ids = {row[0] for row in session_watched_tmdb_ids.all()}

    return [
        EligibleMovieResponse(
            tmdb_id=m["tmdb_id"],
            title=m["title"],
            year=m["year"],
            poster_path=m["poster_path"],
            vote_average=m["vote_average"],
            genres=m["genres"],
            runtime=m["runtime"],
            vote_count=m["vote_count"],
            mpaa_rating=m["mpaa_rating"],
            via_actor_name=m["via_actor_name"],
            watched=m["tmdb_id"] in watched_ids,
            selectable=m["tmdb_id"] not in watched_ids,
        )
        for m in top5
    ]
