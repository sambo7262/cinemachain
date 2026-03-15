# Phase 2: Data Foundation - Context

**Gathered:** 2026-03-15
**Status:** Ready for planning

<domain>
## Phase Boundary

Build the data layer: TMDB filmography fetching, PostgreSQL caching, and Plex watch state sync (webhook + manual mark). This phase delivers working data APIs that Phases 3 and 4 will consume — no game session logic, no UI.

</domain>

<decisions>
## Implementation Decisions

### Plex library sync
- Auto-sync Plex watch history on app startup
- No automatic update to active game sessions — if a watched movie intersects an in-progress session, prompt the user to confirm before reflecting the change in session state
- This prompt/conflict behaviour is Phase 3's responsibility; Phase 2 stores watch state only

### Watch state freshness
- No polling in v1 — webhook is the only automatic watch-state update mechanism post-startup
- If a webhook is missed, the user manually marks the movie as watched (DATA-06 fallback)
- Polling deferred; revisit in v2 if missed webhooks prove to be a real pain point

### TMDB fetch strategy
- Lazy/on-demand only in v1 — fetch what the UI requests, cache the result, serve from cache on repeat requests
- No eager pre-fetching of actor filmographies or related movies
- Goal: gauge real-world performance with lazy fetching before committing to a pre-fetch strategy

### Rating source
- TMDB `vote_average` only — no Rotten Tomatoes, no OMDb
- Displayed wherever a rating is shown in Phases 3 and 4

### Webhook handling
- Plex webhooks arrive as `multipart/form-data` — require `python-multipart` and `Form(...)` in FastAPI
- `media.scrobble` fires at ~90% playback; known reliability bugs — DATA-06 manual mark is the documented fallback
- No polling fallback in v1

### Claude's Discretion
- Database schema design (movies, actors, credits, watch_events tables)
- TMDB API client implementation and asyncio.Semaphore rate-limit handling
- Cache invalidation strategy
- SQLAlchemy model structure and relationship design
- Alembic migration files

</decisions>

<specifics>
## Specific Ideas

- All API keys already configured in `settings.py` (TMDB, Plex, Radarr, Sonarr) — no new env vars needed for this phase
- Async SQLAlchemy session factory (`get_db` dependency) already in place — models just need to be added to `Base`

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `app/db.py`: async engine + `AsyncSessionLocal` + `get_db` dependency — Phase 2 models plug directly into this
- `app/settings.py`: `Settings` with `tmdb_api_key`, `plex_token`, `plex_url` already typed and loaded
- `app/models/__init__.py`: empty `Base(DeclarativeBase)` — Phase 2 defines all ORM models here
- `app/dependencies.py`: existing dependency injection pattern to follow

### Established Patterns
- Async-first: all DB access via `AsyncSession`; TMDB HTTP calls should use `httpx.AsyncClient`
- Pydantic Settings for config — add no new env vars without adding a typed field to `Settings`
- Router-per-domain pattern established in `app/routers/`

### Integration Points
- Phase 3 (Movie Game) and Phase 4 (Query Mode) will call the endpoints built here
- Alembic migrations live in `backend/alembic/versions/` — Phase 2 creates the first real migration
- compose.yaml mounts backend data to `/volume1/docker/appdata/cinemachain/backend`

</code_context>

<deferred>
## Deferred Ideas

- CSV upload to seed a game session with an existing actor/movie chain — Phase 3 (session startup flows)
- Plex watch state polling fallback — v2, if missed webhooks prove problematic in production

</deferred>

---

*Phase: 02-data-foundation*
*Context gathered: 2026-03-15*
