# Phase 2: Data Foundation - Research

**Researched:** 2026-03-15
**Domain:** TMDB API integration, async SQLAlchemy ORM design, Plex library sync, Plex webhook handling
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Plex library sync**
- Auto-sync Plex watch history on app startup
- No automatic update to active game sessions — if a watched movie intersects an in-progress session, prompt the user to confirm before reflecting the change in session state
- This prompt/conflict behaviour is Phase 3's responsibility; Phase 2 stores watch state only

**Watch state freshness**
- No polling in v1 — webhook is the only automatic watch-state update mechanism post-startup
- If a webhook is missed, the user manually marks the movie as watched (DATA-06 fallback)
- Polling deferred; revisit in v2 if missed webhooks prove to be a real pain point

**TMDB fetch strategy**
- Lazy/on-demand only in v1 — fetch what the UI requests, cache the result, serve from cache on repeat requests
- No eager pre-fetching of actor filmographies or related movies
- Goal: gauge real-world performance with lazy fetching before committing to a pre-fetch strategy

**Rating source**
- TMDB `vote_average` only — no Rotten Tomatoes, no OMDb
- Displayed wherever a rating is shown in Phases 3 and 4

**Webhook handling**
- Plex webhooks arrive as `multipart/form-data` — require `python-multipart` and `Form(...)` in FastAPI
- `media.scrobble` fires at ~90% playback; known reliability bugs — DATA-06 manual mark is the documented fallback
- No polling fallback in v1

### Claude's Discretion
- Database schema design (movies, actors, credits, watch_events tables)
- TMDB API client implementation and asyncio.Semaphore rate-limit handling
- Cache invalidation strategy
- SQLAlchemy model structure and relationship design
- Alembic migration files

### Deferred Ideas (OUT OF SCOPE)
- CSV upload to seed a game session with an existing actor/movie chain — Phase 3 (session startup flows)
- Plex watch state polling fallback — v2, if missed webhooks prove problematic in production
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| DATA-01 | System fetches movie metadata (poster, rating, year, genres) from TMDB API | TMDB `/3/movie/{id}` endpoint; fields: `id`, `poster_path`, `vote_average`, `release_date`, `genres` |
| DATA-02 | System fetches actor metadata and filmography credits from TMDB API | TMDB `/3/person/{id}` + `/3/person/{id}/movie_credits`; `append_to_response` pattern for single-call fetching |
| DATA-03 | System caches TMDB data in PostgreSQL to respect rate limits | ORM models for `movies`, `actors`, `credits`; lazy fetch + cache-on-first-hit strategy |
| DATA-04 | System cross-references Plex library to determine watched/unwatched state per movie | PlexAPI `PlexServer` with token; `library.search()` returning `guids` for TMDB ID matching; `viewCount > 0` = watched |
| DATA-05 | System receives Plex webhook events to update watch state on playback completion | `media.scrobble` event at 90% mark; multipart/form-data; `python-multipart` + FastAPI `Form(...)` already installed |
| DATA-06 | User can manually mark a movie as watched (fallback without Plex Pass) | `PATCH /movies/{id}/watched` endpoint writing `watch_events` table; no Plex dependency |
</phase_requirements>

---

## Summary

Phase 2 builds the data plumbing that every subsequent phase depends on: a lazy TMDB fetch-and-cache pipeline, a Plex watch-history sync that runs on startup, a webhook listener for real-time scrobble events, and a manual mark-watched fallback. All six DATA requirements are self-contained within this phase.

The existing backend code (db.py, settings.py, models/__init__.py, alembic/env.py) is already wired for async SQLAlchemy 2.0 with PostgreSQL. This phase's primary task is defining ORM models that plug into the existing `Base`, writing the first real Alembic migration, implementing `httpx.AsyncClient` calls against the TMDB v3 REST API, connecting to Plex via `PlexServer(plex_url, token)`, and exposing purpose-built FastAPI routers for each domain.

The primary risks are: (1) Plex GUID format matching — Plex encodes external IDs as `tmdb://12345` strings in a `guids` list, requiring parsing to join against the TMDB integer IDs stored in the database; (2) the Plex webhook payload arrives as `multipart/form-data` with the JSON encoded in the `payload` form field, not as a JSON body — a common integration error; (3) SQLAlchemy async sessions prohibit implicit lazy loading, requiring `selectinload()` on all relationship traversals.

**Primary recommendation:** Implement the TMDB client as a standalone `app/services/tmdb.py` module using a single shared `httpx.AsyncClient` with an `asyncio.Semaphore(10)` concurrency cap; keep Plex sync in `app/services/plex.py`; expose data via routers under `app/routers/movies.py`, `app/routers/actors.py`, and `app/routers/plex.py`.

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| httpx | 0.27.2 (pinned) | Async TMDB API calls | Already in requirements.txt; native asyncio support; no callback hell |
| sqlalchemy[asyncio] | 2.0.36 (pinned) | Async ORM + query builder | Already configured in db.py with asyncpg driver |
| asyncpg | 0.29.0 (pinned) | PostgreSQL async driver | Required by SQLAlchemy async engine |
| alembic | 1.13.3 (pinned) | Schema migrations | Already configured in alembic/env.py with async pattern |
| python-multipart | 0.0.12 (pinned) | Parse Plex webhook multipart bodies | Already in requirements.txt; FastAPI Form() depends on it |
| plexapi | 4.18.0 | Plex library sync (startup) | Synchronous library; run in thread pool for startup sync only |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pytest-asyncio | 0.24.0 (pinned) | Async test support | Already in requirements.txt; asyncio_mode=auto in pytest.ini |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Raw httpx calls to TMDB | tmdbv3api or themoviedb wrapper | Wrappers add another dependency with sync-first design; raw httpx is already present and async-native |
| PlexAPI for webhooks | Raw FastAPI multipart parsing | PlexAPI is synchronous and not suited for webhook handling; use FastAPI Form() directly |
| asyncio.Semaphore for TMDB rate-limit | aiolimiter or aiometer | Extra dependency not needed at TMDB's ~40 req/s ceiling; Semaphore is stdlib |

**Installation — no new packages needed.** All required libraries are already in `requirements.txt`:
```bash
# Already installed: fastapi, uvicorn, sqlalchemy[asyncio], asyncpg, alembic,
# pydantic-settings, python-dotenv, python-multipart, httpx, pytest, pytest-asyncio
# Add only:
pip install plexapi==4.18.0
```

Add `plexapi==4.18.0` to `requirements.txt`.

---

## Architecture Patterns

### Recommended Project Structure

```
backend/app/
├── models/
│   └── __init__.py          # Movie, Actor, Credit, WatchEvent ORM models (adds to existing Base)
├── services/
│   ├── tmdb.py              # TMDBClient class — lazy fetch + cache logic
│   └── plex.py              # PlexSyncService — startup library sync + webhook processing
├── routers/
│   ├── health.py            # Existing
│   ├── movies.py            # GET /movies/{id}, PATCH /movies/{id}/watched
│   ├── actors.py            # GET /actors/{id}/filmography
│   └── plex.py              # POST /webhooks/plex (scrobble listener)
├── db.py                    # Existing — no changes
├── dependencies.py          # Existing — add tmdb_client dependency
├── main.py                  # Add: Plex startup sync in lifespan, include new routers
└── settings.py              # Existing — no changes (all keys already present)

backend/alembic/versions/
└── 20260315_XXXX_initial_data_schema.py   # First real migration
```

### Pattern 1: Lazy Fetch with PostgreSQL Cache (DATA-01, DATA-02, DATA-03)

**What:** Check DB first; if missing, fetch from TMDB, store, return.
**When to use:** Every TMDB-sourced endpoint — movie details and actor filmography.

```python
# Source: pattern derived from CONTEXT.md decisions + SQLAlchemy 2.0 docs
async def get_movie(tmdb_id: int, db: AsyncSession, client: TMDBClient) -> Movie:
    result = await db.execute(select(Movie).where(Movie.tmdb_id == tmdb_id))
    movie = result.scalar_one_or_none()
    if movie is None:
        data = await client.fetch_movie(tmdb_id)
        movie = Movie(**data)
        db.add(movie)
        await db.commit()
        await db.refresh(movie)
    return movie
```

### Pattern 2: SQLAlchemy Async — Always Eager-Load Relationships

**What:** Use `selectinload()` for any relationship traversal. Async sessions reject implicit lazy loading.
**When to use:** Any query that accesses `movie.credits`, `actor.credits`, or `credit.movie`.

```python
# Source: https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html
from sqlalchemy.orm import selectinload
stmt = select(Movie).where(Movie.tmdb_id == tmdb_id).options(
    selectinload(Movie.credits).selectinload(Credit.actor)
)
result = await db.execute(stmt)
movie = result.scalar_one_or_none()
```

### Pattern 3: TMDB Client with Concurrency Cap

**What:** Shared `httpx.AsyncClient` instance with `asyncio.Semaphore` to cap concurrent TMDB requests.
**When to use:** All TMDB HTTP calls. TMDB allows ~40 req/s; Semaphore(10) is a safe conservative cap for a NAS workload.

```python
# Source: asyncio docs + TMDB rate limit guidance
class TMDBClient:
    BASE_URL = "https://api.themoviedb.org/3"

    def __init__(self, api_key: str):
        self._client = httpx.AsyncClient(
            base_url=self.BASE_URL,
            params={"api_key": api_key},
            timeout=10.0,
        )
        self._sem = asyncio.Semaphore(10)

    async def fetch_movie(self, tmdb_id: int) -> dict:
        async with self._sem:
            r = await self._client.get(f"/movie/{tmdb_id}", params={"append_to_response": "credits"})
            r.raise_for_status()
            return r.json()

    async def fetch_person(self, person_id: int) -> dict:
        async with self._sem:
            r = await self._client.get(f"/person/{person_id}/movie_credits")
            r.raise_for_status()
            return r.json()

    async def close(self):
        await self._client.aclose()
```

Instantiate once in `lifespan` and expose via a FastAPI dependency.

### Pattern 4: Plex Webhook — multipart/form-data Parsing

**What:** Plex POSTs a `multipart/form-data` body where the field named `payload` contains the JSON string.
**When to use:** `POST /webhooks/plex` endpoint only.

```python
# Source: Plex support docs + FastAPI Form() docs
import json
from fastapi import APIRouter, Form

router = APIRouter()

@router.post("/webhooks/plex")
async def plex_webhook(payload: str = Form(...)):
    event = json.loads(payload)
    if event.get("event") == "media.scrobble":
        metadata = event.get("Metadata", {})
        # metadata["guid"] or metadata["Guid"] list contains tmdb://XXXX entries
        await handle_scrobble(metadata)
    return {"status": "ok"}
```

**Critical:** The endpoint MUST accept `Form(...)` not `Body(...)`. If declared as JSON body, FastAPI will reject multipart requests with a 422.

### Pattern 5: Plex Library Sync on Startup (DATA-04)

**What:** On app startup, iterate the Plex Movies library and sync watched state for every movie that already exists in the local database.
**When to use:** `lifespan` startup hook in main.py, wrapped in `asyncio.get_event_loop().run_in_executor` because PlexAPI is synchronous.

```python
# Source: python-plexapi docs
from plexapi.server import PlexServer

def _sync_plex_watched(plex_url: str, plex_token: str) -> list[dict]:
    """Synchronous — called from run_in_executor."""
    plex = PlexServer(plex_url, plex_token)
    movies = plex.library.section("Movies").search()
    results = []
    for m in movies:
        tmdb_id = None
        for guid in m.guids:
            if guid.id.startswith("tmdb://"):
                tmdb_id = int(guid.id.replace("tmdb://", ""))
        if tmdb_id:
            results.append({"tmdb_id": tmdb_id, "watched": m.isWatched, "view_count": m.viewCount})
    return results
```

Then in the async lifespan, call via executor and bulk-upsert `watch_events` rows.

**Note:** `plexapi.server.PlexServer` is synchronous. Do NOT await it. Run with `loop.run_in_executor(None, _sync_plex_watched, url, token)`.

### Anti-Patterns to Avoid

- **Declaring the Plex webhook route as `async def` with `body: SomeModel`:** FastAPI will read the body as JSON, fail on multipart, return 422.
- **Lazy loading in async context:** Accessing `movie.credits` without `selectinload()` raises `MissingGreenlet` / `greenlet_spawn` errors at runtime in async SQLAlchemy.
- **Calling PlexAPI directly in an async route without run_in_executor:** Blocks the event loop; causes timeouts on NAS hardware.
- **Storing TMDB poster_path as full URL:** TMDB returns a relative path like `/abc123.jpg`. Prepend `https://image.tmdb.org/t/p/w500` at display time, not in the database.
- **Using `expire_on_commit=True` (default):** All attributes expire after commit, causing implicit I/O on attribute access in async context. `AsyncSessionLocal` already sets `expire_on_commit=False` — do not override.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| TMDB image URL construction | Custom URL builder | Prepend `https://image.tmdb.org/t/p/w500{poster_path}` | One-liner; TMDB image base URL is stable and documented |
| Schema migration | Manual `CREATE TABLE` SQL | Alembic autogenerate | env.py is already wired; `alembic revision --autogenerate` does it |
| Plex GUID parsing | Regex on guids string | `guid.id.startswith("tmdb://")` + `int(guid.id.split("//")[1])` | PlexAPI returns parsed `Guid` objects with `.id` attribute |
| HTTP retry logic | Custom backoff loop | httpx `raise_for_status()` + caller-level try/except | TMDB rarely 429s at lazy-fetch volume; full retry infra is over-engineering for v1 |
| Watch event deduplication | Custom EXISTS query | PostgreSQL unique constraint on `(user_id, tmdb_id)` in watch_events | DB enforces it; use `INSERT ... ON CONFLICT DO NOTHING` (SQLAlchemy `insert().on_conflict_do_nothing()`) |

**Key insight:** The Plex GUID format (`tmdb://12345`) is the only join key between Plex items and the TMDB-keyed database. This string-to-int parsing is the single most critical data plumbing step in the entire phase.

---

## Common Pitfalls

### Pitfall 1: Plex Webhook Body Mis-declared
**What goes wrong:** Route declared with a Pydantic model as JSON body — returns 422 on every webhook because Plex sends multipart.
**Why it happens:** Developers test locally with `curl -d '{"event":"..."}` -H 'Content-Type: application/json'` before testing with actual Plex.
**How to avoid:** Always declare as `payload: str = Form(...)`. Parse JSON inside the handler with `json.loads(payload)`.
**Warning signs:** 422 Unprocessable Entity in logs immediately on webhook delivery; Plex shows webhook as failed.

### Pitfall 2: SQLAlchemy `MissingGreenlet` / Implicit Lazy Load
**What goes wrong:** Accessing `movie.credits` after fetching `movie` without `selectinload` raises an error at runtime, not at query time.
**Why it happens:** SQLAlchemy async transparently defers loading, but there's no greenlet to run the implicit IO in an async context.
**How to avoid:** Add `selectinload()` to every query that touches a relationship. As a safety net, add `lazy="raise"` to relationship definitions so lazy access fails loudly during development.
**Warning signs:** `sqlalchemy.exc.MissingGreenlet` traceback in production but not in sync tests.

### Pitfall 3: TMDB `append_to_response` Field Naming
**What goes wrong:** Movie credits fetched via `append_to_response=credits` arrive under `response["credits"]["cast"]` — not `response["cast"]`. Accessing `response["cast"]` returns `None`.
**Why it happens:** `append_to_response` nests extra responses under their endpoint name.
**How to avoid:** Access as `data["credits"]["cast"]` when using append_to_response, or make a separate `/movie/{id}/credits` call.
**Warning signs:** Cast list is always empty on first fetch but movies store correctly.

### Pitfall 4: PlexAPI Blocking the Event Loop
**What goes wrong:** Calling `PlexServer(url, token)` or iterating `library.search()` inside an `async def` blocks the event loop for potentially several seconds (Plex library can have thousands of movies).
**Why it happens:** PlexAPI is synchronous and performs HTTP calls synchronously.
**How to avoid:** Wrap in `asyncio.get_event_loop().run_in_executor(None, sync_fn)` for the startup sync. Never call PlexAPI in a request handler.
**Warning signs:** FastAPI health endpoint times out during startup.

### Pitfall 5: TMDB Poster Path Stored vs. Displayed
**What goes wrong:** TMDB returns `poster_path` as `/abc123.jpg`. Storing the full URL (`https://image.tmdb.org/t/p/w500/abc123.jpg`) couples data to a specific image size.
**Why it happens:** Developers construct the full URL once and store it.
**How to avoid:** Store the raw path from TMDB. Construct the full URL in response schemas or on the frontend. The base URL is `https://image.tmdb.org/t/p/w500`.
**Warning signs:** Phase 3 or 4 needs a different poster size and every row must be updated.

### Pitfall 6: Plex `media.scrobble` Double-Fire / Missed Events
**What goes wrong:** `media.scrobble` fires at ~90% completion, has documented reliability bugs, and can fire twice for the same viewing.
**Why it happens:** Known Plex webhook issue documented in the official Plex support article.
**How to avoid:** Make `handle_scrobble` idempotent — use `INSERT INTO watch_events ... ON CONFLICT (tmdb_id) DO NOTHING` rather than a plain insert.
**Warning signs:** Same movie appears as watched twice in logs; or watch state not updated after full playback.

---

## Code Examples

Verified patterns from official sources and existing project code:

### SQLAlchemy ORM Model Definitions

```python
# Source: SQLAlchemy 2.0 docs + existing app/models/__init__.py Base
from datetime import datetime
from sqlalchemy import Integer, String, Float, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models import Base


class Movie(Base):
    __tablename__ = "movies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tmdb_id: Mapped[int] = mapped_column(Integer, unique=True, nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    year: Mapped[int | None] = mapped_column(Integer)
    poster_path: Mapped[str | None] = mapped_column(String(512))
    vote_average: Mapped[float | None] = mapped_column(Float)
    genres: Mapped[str | None] = mapped_column(String(512))  # JSON-encoded list
    fetched_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    credits: Mapped[list["Credit"]] = relationship(
        back_populates="movie", lazy="raise"
    )
    watch_events: Mapped[list["WatchEvent"]] = relationship(
        back_populates="movie", lazy="raise"
    )


class Actor(Base):
    __tablename__ = "actors"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tmdb_id: Mapped[int] = mapped_column(Integer, unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    profile_path: Mapped[str | None] = mapped_column(String(512))
    fetched_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    credits: Mapped[list["Credit"]] = relationship(
        back_populates="actor", lazy="raise"
    )


class Credit(Base):
    """Association between Movie and Actor (many-to-many via explicit table)."""
    __tablename__ = "credits"
    __table_args__ = (UniqueConstraint("movie_id", "actor_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    movie_id: Mapped[int] = mapped_column(ForeignKey("movies.id"), nullable=False, index=True)
    actor_id: Mapped[int] = mapped_column(ForeignKey("actors.id"), nullable=False, index=True)
    character: Mapped[str | None] = mapped_column(String(255))
    order: Mapped[int | None] = mapped_column(Integer)  # billing order from TMDB

    movie: Mapped["Movie"] = relationship(back_populates="credits", lazy="raise")
    actor: Mapped["Actor"] = relationship(back_populates="credits", lazy="raise")


class WatchEvent(Base):
    __tablename__ = "watch_events"
    __table_args__ = (UniqueConstraint("tmdb_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tmdb_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    movie_id: Mapped[int | None] = mapped_column(ForeignKey("movies.id"))
    source: Mapped[str] = mapped_column(String(50), nullable=False)  # "plex_sync" | "plex_webhook" | "manual"
    watched_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    movie: Mapped["Movie | None"] = relationship(back_populates="watch_events", lazy="raise")
```

### Alembic: Generate First Migration

```bash
# Run from backend/ directory with DATABASE_URL in environment
alembic revision --autogenerate -m "initial_data_schema"
alembic upgrade head
```

Alembic env.py already imports `Base.metadata` — models just need to be imported before migration runs.

### TMDB Movie Response Field Map

```
GET /3/movie/{movie_id}?append_to_response=credits

Response fields used:
  .id                     → movies.tmdb_id
  .title                  → movies.title
  .release_date[:4]       → movies.year   (e.g. "2019-04-26" → 2019)
  .poster_path            → movies.poster_path  (e.g. "/abc.jpg")
  .vote_average           → movies.vote_average
  .genres[].name          → movies.genres  (JSON-encode list)
  .credits.cast[].id      → actors.tmdb_id
  .credits.cast[].name    → actors.name
  .credits.cast[].character → credits.character
  .credits.cast[].order   → credits.order
  .credits.cast[].profile_path → actors.profile_path
```

### TMDB Person Movie Credits Field Map

```
GET /3/person/{person_id}/movie_credits

Response fields used:
  .cast[].id              → movies.tmdb_id
  .cast[].title           → movies.title
  .cast[].release_date    → movies.year
  .cast[].poster_path     → movies.poster_path
  .cast[].vote_average    → movies.vote_average
  .cast[].character       → credits.character
  .cast[].genre_ids       → (integer IDs; resolve genre names via /3/genre/movie/list or store as-is)
```

### FastAPI Lifespan with Plex Startup Sync

```python
# Source: existing app/main.py lifespan pattern + asyncio run_in_executor
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Start TMDB client
    tmdb_client = TMDBClient(api_key=settings.tmdb_api_key)
    app.state.tmdb_client = tmdb_client

    # Startup DB check (existing)
    async with engine.begin() as conn:
        await conn.execute(text("SELECT 1"))

    # Plex startup sync (non-blocking)
    loop = asyncio.get_event_loop()
    try:
        watched_items = await loop.run_in_executor(
            None, _sync_plex_watched, settings.plex_url, settings.plex_token
        )
        async with AsyncSessionLocal() as db:
            await _upsert_watch_events(db, watched_items, source="plex_sync")
    except Exception as exc:
        # Plex unavailable at startup is non-fatal
        logger.warning("Plex startup sync failed: %s", exc)

    yield

    await tmdb_client.close()
    await engine.dispose()
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| SQLAlchemy 1.4 `session.query()` style | 2.0 `select()` + `await session.execute()` | SQLAlchemy 2.0 (2023) | All queries must use 2.0 style in async context |
| Alembic sync engine in env.py | Async engine + `run_sync()` wrapper | Alembic ~1.8 (2022) | env.py already uses the correct async pattern |
| `relationship(lazy="select")` default | `lazy="raise"` + explicit `selectinload()` | SQLAlchemy async best practice | Prevents silent lazy-load hangs in async code |
| PlexAPI `watchHistory()` method | `library.section().search()` with `guids` | Current PlexAPI 4.x | `guids` is the canonical way to match Plex items to TMDB IDs |

**Deprecated/outdated:**
- `tmdbv3api` library: Synchronous-first, adds unnecessary wrapper over a simple REST API; not used in this project
- `session.query(Model)` style: Works in sync contexts, but `select(Model)` is the 2.0 canonical approach required for async

---

## Open Questions

1. **PlexAPI `plex_url` format — local IP vs. Tailscale hostname**
   - What we know: `settings.plex_url` is configured in `.env`; PlexAPI `PlexServer(baseurl, token)` accepts any reachable URL
   - What's unclear: Whether the NAS resolves the Plex URL inside the Docker network at startup
   - Recommendation: Use the LAN IP for startup sync (most reliable); document in `.env.example`

2. **TMDB genre IDs in `person/movie_credits` response**
   - What we know: The `/person/{id}/movie_credits` endpoint returns `genre_ids` as integers, not names
   - What's unclear: Whether to resolve IDs to names at fetch time (extra call) or store raw IDs and resolve on demand
   - Recommendation: Store raw `genre_ids` as a JSON integer array in `movies.genre_ids` column; resolve names in a separate `/3/genre/movie/list` lookup cached at startup. Avoids per-movie extra API calls.

3. **`media.scrobble` metadata GUID format**
   - What we know: Plex webhook `Metadata` object contains `guid` (single string, old agent format) and `Guid` (list, new agent format)
   - What's unclear: Which field is present for modern Plex Movie agent vs. legacy agent movies in the user's library
   - Recommendation: Handle both: check `Metadata["Guid"]` list first for `tmdb://` prefix; fall back to parsing `Metadata["guid"]` string. Makes the handler agent-agnostic.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 8.3.4 + pytest-asyncio 0.24.0 |
| Config file | `backend/pytest.ini` (`asyncio_mode = auto`) |
| Quick run command | `cd backend && pytest tests/test_tmdb.py tests/test_plex_webhook.py -x -q` |
| Full suite command | `cd backend && pytest -x -q` |

### Phase Requirements — Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| DATA-01 | `GET /movies/{id}` returns poster, rating, year, genres from TMDB (first call hits TMDB) | unit (mock httpx) | `pytest tests/test_tmdb.py::test_fetch_movie_details -x` | Wave 0 |
| DATA-02 | `GET /actors/{id}/filmography` returns actor credits from TMDB | unit (mock httpx) | `pytest tests/test_tmdb.py::test_fetch_actor_credits -x` | Wave 0 |
| DATA-03 | Second `GET /movies/{id}` is served from DB without TMDB call | unit (mock httpx + real SQLite/memory DB) | `pytest tests/test_tmdb.py::test_movie_cached_on_repeat_request -x` | Wave 0 |
| DATA-04 | Startup sync writes `watch_events` rows for Plex-watched movies | unit (mock PlexAPI) | `pytest tests/test_plex_sync.py::test_startup_sync_marks_watched -x` | Wave 0 |
| DATA-05 | `POST /webhooks/plex` with `media.scrobble` payload marks movie watched | integration | `pytest tests/test_plex_webhook.py::test_scrobble_marks_watched -x` | Wave 0 |
| DATA-06 | `PATCH /movies/{id}/watched` stores a `watch_events` row with source=manual | unit | `pytest tests/test_movies.py::test_manual_mark_watched -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `cd backend && pytest tests/ -x -q --ignore=tests/test_persistence.py`
- **Per wave merge:** `cd backend && pytest -x -q`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `backend/tests/test_tmdb.py` — covers DATA-01, DATA-02, DATA-03
- [ ] `backend/tests/test_plex_sync.py` — covers DATA-04
- [ ] `backend/tests/test_plex_webhook.py` — covers DATA-05
- [ ] `backend/tests/test_movies.py` — covers DATA-06

Existing infrastructure (`conftest.py`, `pytest.ini`, `pytest-asyncio`) requires no changes.

---

## Sources

### Primary (HIGH confidence)
- TMDB API docs (https://developer.themoviedb.org/reference/movie-details) — movie details endpoint fields
- TMDB API docs (https://developer.themoviedb.org/reference/person-movie-credits) — actor credits endpoint
- TMDB API rate limit docs (https://developer.themoviedb.org/reference/rate-limiting) — ~40 req/s ceiling, 429 handling
- SQLAlchemy 2.0 async docs (https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html) — selectinload, AsyncSession, expire_on_commit
- Plex webhook support article (https://support.plex.tv/articles/115002267687-webhooks/) — event types, multipart payload, media.scrobble behavior
- Existing `backend/requirements.txt` — verified installed package versions
- Existing `backend/app/db.py`, `app/settings.py`, `app/models/__init__.py` — confirmed async engine setup and Base

### Secondary (MEDIUM confidence)
- python-plexapi readthedocs (https://python-plexapi.readthedocs.io/en/latest/modules/video.html) — Movie attributes (ratingKey, guids, isWatched, viewCount)
- python-plexapi readthedocs (https://python-plexapi.readthedocs.io/en/latest/modules/library.html) — library.search() filter patterns
- FastAPI docs (https://fastapi.tiangolo.com/tutorial/request-forms/) — Form() usage for multipart

### Tertiary (LOW confidence)
- WebSearch: PlexAPI GUID format `tmdb://XXXX` — consistent across multiple community sources but not formally documented in API spec; treat as stable convention

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries pinned in requirements.txt; already installed and tested
- Architecture: HIGH — TMDB REST API is stable; SQLAlchemy 2.0 async patterns verified against official docs
- TMDB field mapping: HIGH — verified against official reference docs
- Plex GUID format: MEDIUM — documented in PlexAPI readthedocs and multiple community sources; exact format stable since Plex Movie agent introduction
- Webhook parsing: HIGH — official Plex support article confirms multipart/form-data + `payload` field name
- Pitfalls: HIGH — all six pitfalls are either from official docs or the existing STATE.md accumulated context

**Research date:** 2026-03-15
**Valid until:** 2026-06-15 (TMDB v3 and PlexAPI 4.x are stable; SQLAlchemy 2.0 API is stable)
