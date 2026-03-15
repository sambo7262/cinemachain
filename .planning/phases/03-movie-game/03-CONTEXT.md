# Phase 3: Movie Game - Context

**Gathered:** 2026-03-15
**Status:** Ready for planning

<domain>
## Phase Boundary

Complete the actor-chain game loop: start a session (via watched movie selection, title search, or CSV import), navigate Eligible Actors and Eligible Movies panels with sort/filter controls, queue a chosen movie via Radarr, and advance the session once the movie is marked as watched. Session state fully persisted to PostgreSQL. This phase also establishes the frontend — the React app replacing the current placeholder.

</domain>

<decisions>
## Implementation Decisions

### Game startup options
- User can start a session by selecting any previously watched movie (from watch history in the app)
- User can start by searching/querying any movie title — does not need to have been watched on Plex (user may have watched it on another service)
- User can import an existing chain via CSV (columns: Movie Name, Actor Name, Order integer) — TMDB lookup resolves names to correct TMDB IDs; if multiple matches found, Claude's discretion on disambiguation strategy (e.g., pick highest vote_count match)
- One session at a time — only one active or paused session exists at any given time

### Session persistence & lifecycle
- Sessions can be explicitly paused from within the app
- While paused: incoming Plex watch events do NOT affect session state
- If a Plex webhook fires for a movie and there is no active (unpaused) session matching it → no auto-session creation, event is ignored for game purposes
- Session ends when: user manually terminates it, OR the chain fully exhausts (all eligible actors across all reachable movies have been picked and their filmographies are fully watched)
- Paused sessions can be resumed from the app

### UI layout — two-tab game panel
- Frontend stack: React + Vite + Tailwind CSS + shadcn/ui
- Game view uses a two-tab layout: **Eligible Actors** tab | **Eligible Movies** tab
- Session starts with Eligible Actors tab active, showing the starting movie's cast (excluding actors already picked in this session)
- Selecting an actor switches to Eligible Movies tab showing that actor's filmography (unwatched movies by default)
- Viewing Eligible Movies tab without first selecting an actor shows ALL eligible movies across all currently eligible actors (combined view)
- Movie cards display: poster, title, TMDB vote_average rating, genre(s), runtime, and "via [Actor Name]" in combined/all-actors view
- Movies can be sorted and filtered by rating, genre, and runtime
- Toggle: unwatched-only vs all movies with watched badges; only unwatched movies are selectable

### Chain history display
- Visible chain display in the game UI showing the full sequence: Movie → Actor → Movie → Actor → ...
- Table format is acceptable as a baseline; Claude has discretion to make it visually compelling — user wants it to feel like "a fun visual story" rather than a plain list

### Session advancement
- Session advances only after the chosen movie is marked as watched (via Plex webhook or manual mark)
- UI prompts the user: "[Movie] marked as watched — [Continue the chain]"
- User taps Continue → Eligible Actors panel reloads for the newly watched movie

### Radarr integration
- Radarr download request only triggered when: user selects a movie to watch AND the movie does not already exist in Radarr
- If movie already exists in Radarr (monitored or downloaded) → skip Radarr API call; session waits for watched event as normal
- No Radarr call at session start — only at the point the user picks a movie to request

### Frontend — new app setup
- Replace the current `frontend/index.html` placeholder with a full React + Vite project
- Dark theme by default (matches the existing placeholder's dark aesthetic)
- Responsive layout targeting TV and tablet use ("on the couch" primary context — large tap targets, readable at distance)

### Claude's Discretion
- TMDB name-to-ID disambiguation strategy when CSV lookup returns multiple matches
- Chain history visual treatment (beyond the table baseline — make it feel like a story)
- Game session and step ORM schema design
- RadarrClient service implementation (mirrors TMDBClient pattern)
- Frontend routing approach (likely single-page with React Router or TanStack Router)
- Exact shadcn/ui component choices for tabs, cards, filters, and chain history

</decisions>

<specifics>
## Specific Ideas

- "a 'chain' may visually be difficult — its easy to show this as a table as well with a watch order. open to fun ui ideas here that make it a fun visual story"
- Movie card in combined Movies view should show "via [Actor Name]" so the chain logic is visible to the user
- The app is primarily used by two people at home (wife and user) — single-user session model is correct; no auth needed

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `app/models/__init__.py`: Movie, Actor, Credit, WatchEvent ORM models — Phase 3 adds GameSession + GameSessionStep models alongside these
- `app/routers/movies.py`: GET /movies/{tmdb_id} — returns watched state; game APIs build on this
- `app/routers/actors.py`: GET /actors/{tmdb_id}/filmography — returns credits with watched flags; Eligible Movies panel queries this
- `app/services/tmdb.py`: TMDBClient — RadarrClient should follow the same httpx.AsyncClient + app.state pattern
- `app/settings.py`: `radarr_url` and `radarr_api_key` already typed and loaded — no new env vars needed for Radarr
- `app/db.py`: async engine + `get_db` dependency — game session queries plug in directly

### Established Patterns
- Async-first: all DB access via `AsyncSession`; RadarrClient uses `httpx.AsyncClient`
- Router-per-domain: new `app/routers/game.py` follows the same structure as movies/actors routers
- `app.state` for shared clients: RadarrClient initialized in lifespan and attached to `app.state`
- `pg_insert(...).on_conflict_do_nothing(...)` pattern for upserts already established

### Integration Points
- Game session APIs consume Phase 2 endpoints (movie details, filmography, watch state)
- Plex webhook router (`app/routers/plex.py`) will need to notify active game sessions when a watch event fires — game advancement hook lives here
- Frontend container currently serves a static placeholder at port 3111 — full React build output replaces `frontend/index.html`
- Alembic migrations in `backend/alembic/versions/` — Phase 3 creates migration for GameSession + GameSessionStep tables

</code_context>

<deferred>
## Deferred Ideas

- "Most connectable" actor sort (actors appearing in most unwatched movies) — GAME-EX-01, v2
- Genre-constrained game mode (e.g., horror-only chain) — GAME-EX-03, v2
- Cross-session chain history / saved chains — GAME-EX-02, v2

</deferred>

---

*Phase: 03-movie-game*
*Context gathered: 2026-03-15*
