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
from app.services.mdblist import fetch_rt_scores
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


class CsvActorOverride(BaseModel):
    row: int
    actor_tmdb_id: int
    actor_name: str


class ImportCSVRequest(BaseModel):
    rows: list[CSVRow]
    name: str = "Imported Chain"
    overrides: list[CsvOverride] = []
    actor_overrides: list[CsvActorOverride] = []


class PickActorRequest(BaseModel):
    actor_tmdb_id: int
    actor_name: str


class RequestMovieRequest(BaseModel):
    movie_tmdb_id: int
    movie_title: str | None = None
    skip_actor: bool = False  # BUG-1: set True by frontend Skip button to bypass disambiguation loop
    skip_radarr: bool = False  # When True, skip Radarr add call and set radarr_status="skipped"


class RenameSessionRequest(BaseModel):
    name: str


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
    overview: str | None = None
    via_actor_name: str | None = None
    watched: bool = False
    selectable: bool = True
    movie_title: str
    rt_score: int | None = None


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
        logger.debug("MPAA tmdb_id=%d: cert=%r", tmdb_id, cert)
        return cert
    except Exception:
        logger.exception("Failed to fetch MPAA rating for tmdb_id=%d", tmdb_id)
        # Don't store sentinel — leave as None so it retries next load
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
            overview_val = data.get("overview")
            await db.execute(
                sa.update(Movie).where(Movie.tmdb_id == tmdb_id).values(
                    genres=genres_json,
                    runtime=runtime_val,
                    overview=overview_val,
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


async def _prefetch_actor_credits_background(
    actor_tmdb_id: int,
    tmdb: TMDBClient,
) -> None:
    """Background task: pre-populate Credit rows for a selected actor's full filmography.

    Called when the user picks an actor so their eligible movies are ready before
    the Eligible Movies tab renders. Mirrors _prefetch_credits_background pattern.
    ENH-1: reduces perceived latency on actor selection.
    """
    try:
        async with _bg_session_factory() as db:
            await _ensure_actor_credits_in_db(actor_tmdb_id, tmdb, db)
    except Exception:
        pass


async def _backfill_movie_posters_background(
    movie_tmdb_ids: list[int],
    tmdb: TMDBClient,
) -> None:
    """Background task: fetch /movie/{id} details for each imported movie and upsert poster_path.

    CSV-imported sessions create GameSessionStep rows but never run the normal TMDB search
    or actor-filmography paths that populate Movie.poster_path. This task backfills poster_path
    (and title/year as a bonus) so the poster wall can render imported sessions correctly.
    """
    async with _bg_session_factory() as db:
        for tmdb_id in movie_tmdb_ids:
            try:
                r = await tmdb._client.get(f"/movie/{tmdb_id}")
                r.raise_for_status()
                data = r.json()
                stmt = pg_insert(Movie).values(
                    tmdb_id=tmdb_id,
                    title=data.get("title", ""),
                    year=int(data["release_date"][:4]) if data.get("release_date") else None,
                    poster_path=data.get("poster_path"),
                    vote_average=data.get("vote_average"),
                    vote_count=data.get("vote_count"),
                    overview=data.get("overview"),
                    genres=None,
                ).on_conflict_do_update(
                    index_elements=["tmdb_id"],
                    set_={
                        "title": data.get("title", ""),
                        "year": int(data["release_date"][:4]) if data.get("release_date") else None,
                        "poster_path": data.get("poster_path"),
                        "vote_average": data.get("vote_average"),
                        "vote_count": data.get("vote_count"),
                        "overview": data.get("overview"),
                    },
                )
                await db.execute(stmt)
                await db.commit()
            except Exception:
                continue  # degrade gracefully — poster wall falls back to CDN or skips


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


async def _resolve_actor_tmdb_id(name: str, tmdb: TMDBClient) -> tuple[int | None, str | None, list[dict]]:
    """Search TMDB for a person by name; return (tmdb_id, canonical_name, suggestions) tuple.

    canonical_name is the TMDB-verified spelling — use this in stored steps (not the raw CSV input).
    suggestions is a list of top-3 {tmdb_id, name} dicts for disambiguation.
    Returns (None, None, []) if no results.
    """
    r = await tmdb._client.get("/search/person", params={"query": name})
    results = r.json().get("results", [])
    if not results:
        return None, None, []
    top3 = results[:3]
    suggestions = [{"tmdb_id": p["id"], "name": p.get("name", "")} for p in top3]
    return results[0]["id"], results[0].get("name"), suggestions


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

    # Build override lookups
    override_map: dict[int, int] = {o.row: o.tmdb_id for o in body.overrides}
    actor_override_map: dict[int, CsvActorOverride] = {o.row: o for o in body.actor_overrides}

    steps_data = []
    step_order = 0
    unresolved: list[dict] = []
    actor_errors: list[dict] = []
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
                if i in actor_override_map:
                    ao = actor_override_map[i]
                    actor_id, canonical_name = ao.actor_tmdb_id, ao.actor_name
                else:
                    actor_id, canonical_name, actor_suggestions = await _resolve_actor_tmdb_id(row.actorName, tmdb)
                if actor_id is None:
                    actor_errors.append({
                        "row": i,
                        "csv_movie_title": row.movieName,
                        "csv_actor_name": row.actorName,
                        "reason": "actor_not_found",
                        "suggestions": actor_suggestions,
                    })
                    # Do NOT append actor step — skip it; movie step already added above
                else:
                    steps_data.append({
                        "step_order": step_order,
                        "movie_tmdb_id": movie_id,
                        "movie_title": row.movieName,
                        "actor_tmdb_id": actor_id,
                        "actor_name": canonical_name,
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
    if unresolved or actor_errors:
        return JSONResponse(
            status_code=200,
            content={
                "status": "validation_required",
                "resolved_count": resolved_count,
                "unresolved": unresolved,
                "actor_errors": actor_errors,
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
        # Item 1: If actor_tmdb_id is set but actor_name is missing, resolve name from TMDB.
        # Handles cases where a raw TMDB ID was entered as an actor override and name was NULL.
        if step.actor_tmdb_id and not step.actor_name:
            try:
                person_data = await tmdb.fetch_person(step.actor_tmdb_id)
                if person_data:
                    step.actor_name = person_data.get("name")
            except Exception:
                pass  # Non-critical — name stays None; chain history degrades gracefully
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

    # Backfill poster_path for all imported movies via /movie/{id}.
    # CSV import bypasses the normal TMDB search/filmography paths that populate poster_path,
    # leaving Movie stubs with poster_path=NULL and breaking the poster wall.
    all_movie_ids = list({s["movie_tmdb_id"] for s in steps_data})
    background_tasks.add_task(_backfill_movie_posters_background, all_movie_ids, tmdb)

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
        runtime_map = await _enrich_steps_runtime(s.steps, db)
        out.append(_build_session_response(s, wa_map, current_movie_title=_resolve_current_movie_title(s), runtime_map=runtime_map))
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
        runtime_map = await _enrich_steps_runtime(s.steps, db)
        out.append(_build_session_response(s, wa_map, current_movie_title=_resolve_current_movie_title(s), runtime_map=runtime_map))
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


@router.patch("/sessions/{session_id}/name", response_model=GameSessionResponse)
async def rename_session(
    session_id: int,
    body: RenameSessionRequest,
    db: AsyncSession = Depends(get_db),
):
    """Rename a session. Returns 400 for invalid name, 404 if not found, 409 if name taken."""
    # Validate name
    name = body.name.strip() if body.name else ""
    if not name:
        raise HTTPException(status_code=400, detail="Session name cannot be empty")
    if len(name) > 100:
        raise HTTPException(status_code=400, detail="Session name must be 100 characters or fewer")

    # Check uniqueness among active sessions (excluding self)
    existing = await db.execute(
        select(GameSession).where(
            GameSession.name == name,
            GameSession.id != session_id,
            GameSession.status.not_in(["archived", "ended"]),
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="A session with that name already exists")

    # Load session
    result = await db.execute(
        select(GameSession)
        .where(GameSession.id == session_id)
        .options(selectinload(GameSession.steps))
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    session.name = name
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
    poster_map, profile_map = await _enrich_steps_thumbnails(session.steps, db)
    runtime_map = await _enrich_steps_runtime(session.steps, db)
    return _build_session_response(
        session, wa_map,
        current_movie_title=_resolve_current_movie_title(session),
        poster_map=poster_map,
        profile_map=profile_map,
        runtime_map=runtime_map,
    )


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
    poster_map, profile_map = await _enrich_steps_thumbnails(session.steps, db)
    runtime_map = await _enrich_steps_runtime(session.steps, db)
    return _build_session_response(
        session, wa_map,
        current_movie_title=_resolve_current_movie_title(session),
        poster_map=poster_map,
        profile_map=profile_map,
        runtime_map=runtime_map,
    )


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

    # ELIGIBILITY SCOPE INVARIANT (BUG-3 confirmed):
    # Eligible actors = cast of current_movie_tmdb_id MINUS already-picked actors.
    # Previous chain movies have NO bearing on eligibility.
    # The .where(Movie.tmdb_id == session.current_movie_tmdb_id) below enforces this.
    # Symptom reports of out-of-scope actors are data integrity issues (stale Credit rows),
    # not query logic bugs. The queries are correct as written.

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
    sort_dir: str | None = Query(default="desc"),
    search: str | None = Query(default=None),
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
                    "overview": movie.overview,
                    "genres": movie.genres,
                    "runtime": movie.runtime,
                    "watched": movie.tmdb_id in watched_ids,
                    "selectable": movie.tmdb_id not in watched_ids and movie.tmdb_id not in chain_movie_ids,
                    "via_actor_name": actor.name,
                    "rt_score": movie.rt_score if movie.rt_score and movie.rt_score > 0 else None,
                }
    else:
        # Combined view: get eligible actors first, then their filmographies
        picked_ids = [s.actor_tmdb_id for s in session.steps if s.actor_tmdb_id is not None]

        # BUG-3 scope check: actor_stmt already scoped to current_movie_tmdb_id — correct.
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
                        "overview": movie.overview,
                        "genres": movie.genres,
                        "runtime": movie.runtime,
                        "watched": movie.tmdb_id in watched_ids,
                        "selectable": movie.tmdb_id not in watched_ids and movie.tmdb_id not in chain_movie_ids,
                        "via_actor_name": actor.name,
                        "rt_score": movie.rt_score if movie.rt_score and movie.rt_score > 0 else None,
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

    # Fetch RT scores on-demand from MDBList (if API key configured)
    if movies_map:
        await fetch_rt_scores(list(movies_map.keys()), db)
        await db.commit()
        # Refresh rt_score values in movies_map from DB
        rt_result = await db.execute(
            select(Movie.tmdb_id, Movie.rt_score)
            .where(Movie.tmdb_id.in_(list(movies_map.keys())))
        )
        for row in rt_result.all():
            if row.tmdb_id in movies_map:
                # Don't expose the 0 sentinel to frontend — convert to null
                movies_map[row.tmdb_id]["rt_score"] = row.rt_score if row.rt_score and row.rt_score > 0 else None

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

    # Sort — null-stable two-pass approach: separate nulls first, sort each group, then concat.
    # Nulls always land at the end regardless of sort direction.
    _desc = (sort_dir or "desc") == "desc"
    if sort == "rating":
        rated = [m for m in movies if _effective_rating(m) is not None]
        unrated = [m for m in movies if _effective_rating(m) is None]
        rated.sort(key=lambda m: _effective_rating(m) or 0, reverse=_desc)
        movies = rated + unrated
    elif sort == "runtime":
        with_runtime = [m for m in movies if m.get("runtime") is not None]
        without_runtime = [m for m in movies if m.get("runtime") is None]
        with_runtime.sort(key=lambda m: m["runtime"], reverse=_desc)
        movies = with_runtime + without_runtime
    elif sort == "genre":
        with_genre = [m for m in movies if m.get("genres") and m["genres"] != ""]
        without_genre = [m for m in movies if not m.get("genres") or m["genres"] == ""]
        with_genre.sort(key=lambda m: m["genres"] or "", reverse=_desc)
        movies = with_genre + without_genre
    elif sort == "year":
        with_year = [m for m in movies if m.get("year") is not None]
        without_year = [m for m in movies if m.get("year") is None]
        with_year.sort(key=lambda m: m.get("year") or 0, reverse=_desc)
        movies = with_year + without_year
    elif sort == "mpaa":
        _mpaa_order = {"G": 0, "PG": 1, "PG-13": 2, "R": 3, "NC-17": 4}
        with_mpaa = [m for m in movies if m.get("mpaa_rating") and m.get("mpaa_rating") != ""]
        without_mpaa = [m for m in movies if not m.get("mpaa_rating") or m.get("mpaa_rating") == ""]
        with_mpaa.sort(key=lambda m: _mpaa_order.get(m.get("mpaa_rating") or "", 99), reverse=_desc)
        movies = with_mpaa + without_mpaa
    elif sort == "rt":
        with_rt = [m for m in movies if m.get("rt_score") is not None]
        without_rt = [m for m in movies if m.get("rt_score") is None]
        with_rt.sort(key=lambda m: m.get("rt_score") or 0, reverse=_desc)
        movies = with_rt + without_rt

    # Search — when provided, filter by title (case-insensitive) and bypass pagination.
    # Calls _ensure_actor_credits_in_db to guarantee full filmography coverage (no-op if cached).
    if search:
        search_lower = search.lower()
        # Ensure full filmography is in DB for the actor (short-circuits if already cached)
        if actor_id is not None and hasattr(request.app.state, "tmdb_client"):
            tmdb_for_search: TMDBClient = request.app.state.tmdb_client
            await _ensure_actor_credits_in_db(actor_id, tmdb_for_search, db)
        movies = [m for m in movies if search_lower in m["title"].lower()]
        total = len(movies)
        return {
            "items": movies,
            "total": total,
            "page": 1,
            "page_size": total,
            "has_more": False,
        }

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
    request: Request,
    background_tasks: BackgroundTasks,
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

    # ENH-1: pre-fetch actor's filmography in background so Eligible Movies tab
    # loads faster after actor selection.
    tmdb: TMDBClient = request.app.state.tmdb_client
    background_tasks.add_task(_prefetch_actor_credits_background, body.actor_tmdb_id, tmdb)

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

    # BUG-1: Auto-resolve connecting actor when no explicit pick was made.
    # Check if the most recent step is a movie step (no actor yet) and this is NOT the first pick.
    # skip_actor=True means the user dismissed the disambiguation dialog — bypass entirely.
    last_step = max(session.steps, key=lambda s: s.step_order, default=None)
    previous_movie_tmdb_id = session.current_movie_tmdb_id  # movie being transitioned FROM
    already_picked_ids = [s.actor_tmdb_id for s in session.steps if s.actor_tmdb_id is not None]

    need_actor_auto_resolve = (
        last_step is not None and                        # not the first pick
        last_step.actor_tmdb_id is None and             # last step is a movie step (no actor picked)
        body.movie_tmdb_id != previous_movie_tmdb_id   # actually advancing to a new movie
        and not body.skip_actor                         # BUG-1: skip if user dismissed dialog
    )

    shared_actors: list = []  # defined here to avoid NameError in next_order calculation
    if need_actor_auto_resolve:
        # Find actors appearing in BOTH the previous movie AND the selected movie
        shared_stmt = (
            select(Actor, Credit)
            .join(Credit, Credit.actor_id == Actor.id)
            .join(Movie, Movie.id == Credit.movie_id)
            .where(Movie.tmdb_id == body.movie_tmdb_id)
            .where(Actor.tmdb_id.in_(
                select(Actor.tmdb_id)
                .join(Credit, Credit.actor_id == Actor.id)
                .join(Movie, Movie.id == Credit.movie_id)
                .where(Movie.tmdb_id == previous_movie_tmdb_id)
                .where(Actor.tmdb_id.not_in(already_picked_ids) if already_picked_ids else True)
            ))
        )
        shared_rows = await db.execute(shared_stmt)
        shared_actors = [(actor, credit) for actor, credit in shared_rows.all()]

        if len(shared_actors) > 1:
            # Multiple connecting actors — require user to disambiguate.
            # Do NOT create any steps. Return disambiguation response immediately.
            # Frontend will show a dialog and re-submit after user picks.
            return {
                "status": "disambiguation_required",
                "candidates": [
                    {"tmdb_id": actor.tmdb_id, "name": actor.name}
                    for actor, _ in shared_actors
                ],
                "session": _build_session_response(
                    session,
                    await _enrich_steps_watched_at(session.steps, db),
                    current_movie_title=_resolve_current_movie_title(session),
                ),
            }
        elif len(shared_actors) == 1:
            # Exactly one connecting actor — auto-create the actor step.
            auto_actor, _ = shared_actors[0]
            actor_step_order = max((s.step_order for s in session.steps), default=-1) + 1
            auto_actor_step = GameSessionStep(
                session_id=session.id,
                step_order=actor_step_order,
                movie_tmdb_id=previous_movie_tmdb_id,  # actor was selected FROM this movie
                movie_title=last_step.movie_title,      # title of the previous movie
                actor_tmdb_id=auto_actor.tmdb_id,
                actor_name=auto_actor.name,
            )
            db.add(auto_actor_step)
            # Note: do NOT commit yet — movie step will be added next and committed together
        # If 0 shared actors: fall through to existing movie step creation (no actor step)

    # Add step for the chosen movie
    # Recalculate next_order — may have increased if auto_actor_step was added above
    # (in-session steps list not yet updated, so use explicit calculation)
    existing_max = max((s.step_order for s in session.steps), default=-1)
    auto_step_added = need_actor_auto_resolve and len(shared_actors) == 1
    next_order = existing_max + (2 if auto_step_added else 1)
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
    # skip_radarr=True allows frontend to bypass Radarr (e.g., movie already owned).
    radarr: RadarrClient = request.app.state.radarr_client
    if not body.skip_radarr:
        try:
            radarr_result = await _request_radarr(body.movie_tmdb_id, radarr)
        except Exception:
            radarr_result = {"status": "error"}
    else:
        radarr_result = {"status": "skipped"}

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


