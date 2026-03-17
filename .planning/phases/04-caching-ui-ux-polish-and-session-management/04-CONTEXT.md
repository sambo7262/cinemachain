# Phase 4: Caching, UI/UX Polish, and Session Management — Context

**Gathered:** 2026-03-17
**Status:** Ready for planning

<domain>
## Phase Boundary

Eliminate on-demand TMDB latency through nightly cache pre-population; polish the UI (Radarr notification repositioning, session home poster, full image coverage); add in-session movie suggestions; add session management actions (delete last step, delete archived sessions); redesign movie cards with visible filterable details; widen the app layout with responsive mobile/desktop support; and remove the Watch History tab from session creation.

</domain>

<decisions>
## Implementation Decisions

### Nightly TMDB Cache
- APScheduler runs in-process inside the FastAPI container — auto-starts with Docker, no external setup
- Nightly at 3am (default), configurable via `TMDB_CACHE_TIME=03:00` in .env
- Top-N movies configurable via `TMDB_CACHE_TOP_N=5000` in .env (default 5000)
- **Incremental add-only** — skip movies already in DB (by fetched_at presence), never purge
- DB grows over time; this is expected — vote count threshold ensures only released movies are cached
- No manual trigger (no UI button, no HTTP endpoint) — trust the schedule; admin adjusts top-N via .env if needed

### Radarr Notification Redesign
- **Position:** slim full-width banner rendered immediately below the global NavBar (not inside nav, just beneath it) — never overlaps game controls
- **Text values:** "Already in Radarr" / "Movie Queued for Download" (replaces current verbose messages)
- **Style:** keep existing blue color and size
- **Behavior:** auto-dismiss after 5 seconds; manually dismissible via × button before that

### Session Home Poster Thumbnail
- **Current movie:** large hero poster (portrait ratio, ~120px wide) anchored to the left of the Now Playing card; title + status text sits to the right of the poster
- **Previous movie:** text only — no poster; visual focus stays on the current movie
- Fallback when `poster_path` is null: grey placeholder rectangle at the same dimensions

### Destructive Actions — Delete Last Step
- Confirm dialog required ("Are you sure? This cannot be undone.") before executing
- On confirm: removes the most recent step, reverts `current_movie_tmdb_id` and `current_movie_watched` to prior state
- No Radarr cancellation — download request stays in Radarr regardless
- Session home re-renders to reflect the reverted state

### Destructive Actions — Delete Archived Session
- Confirm dialog required before executing
- On confirm: permanent DB removal of the session and all its steps

### Session Actions Menu
- A `⋯` actions menu button on the session home page houses all session-level actions:
  - Delete last step
  - Export CSV (migrated from wherever it currently lives)
  - (Archive session, if surfaced here)
- Keeps the session home clean — destructive and utility actions are intentionally one level deep

### In-Session Movie Suggestions
- **Location:** own "Suggested" tab alongside Eligible Actors / Eligible Movies (three tabs total in tab view)
- **Count:** always top 5 suggestions — fixed cap regardless of chain depth
- **Ranking:** genre-weighted by the user's watch history (session steps + WatchEvents), tie-broken by TMDB rating (500-vote floor already established)
- **Constraint:** only movies reachable via currently eligible actors are candidates — suggestions are always immediately actionable
- **Card display:** each suggestion shows which eligible actor connects to it ("via [Actor Name]"), plus the full movie card detail set (see below)
- **Watch History tab removed:** the "Watch History" tab on session creation (GameLobby) is removed; session creation retains "Search Title" and "Import Chain" tabs only

### Movie Card Details (Eligible Movies + Suggested tabs)
- Each movie card shows: poster + title + actor name (existing) + **MPAA rating** + **runtime** + **genre tags** + **TMDB rating** (no vote count displayed)
- Everything visible on the card matches what the filter sidebar filters — no need to open the sidebar to understand a movie's attributes
- Actor name on Eligible Movies cards: the eligible actor whose filmography surfaces this movie; on Suggested tab: "via [Actor Name]"

### Filter/Sort Panel
- **Desktop:** persistent sidebar, always visible alongside the movie grid (~200px wide left column); replaces the current collapsible-on-all-screens sidebar
- **Mobile:** sidebar collapses behind a "Filters" toggle button above the movie grid
- Filter categories: Sort by, Genre (multi-select), Runtime (range slider), MPAA Rating (checkboxes) — same as Phase 03.2, just presented in the persistent sidebar

### App Layout — Width and Responsiveness
- **Max width:** 1400px centered; layout expands to fill the screen up to that cap, then centers with horizontal padding
- Removes the current narrow centered container that leaves blank space on wide screens
- **Mobile:** Claude's discretion — apply standard responsive Tailwind breakpoints; prioritize readability and touch targets

### Claude's Discretion
- Mobile breakpoints and exact responsive behavior (column count, spacing, etc.)
- Poster placeholder styling (grey rectangle dimensions, border radius)
- Genre tag chip styling on movie cards
- Session actions menu component (dropdown, popover, or sheet)
- APScheduler job retry behavior on TMDB rate limit hit during nightly run
- Exact sidebar width and layout proportions within the 1400px cap

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Backend — Cache and Scheduler
- `backend/app/routers/game.py` — `_prefetch_credits_background`, `_ensure_actor_credits_in_db`, `_ensure_movie_details_in_db`, `_ensure_movie_cast_in_db` — nightly job reuses these helpers
- `backend/app/services/tmdb.py` — TMDBClient; nightly job uses this for TMDB ID export fetch
- `backend/app/main.py` — lifespan function; APScheduler wired here alongside existing startup logic
- `backend/app/settings.py` — where `TMDB_CACHE_TOP_N` and `TMDB_CACHE_TIME` env vars must be added

### Backend — Session Management
- `backend/app/routers/game.py` — all session endpoints; delete-last-step and delete-archived-session are new endpoints here
- `backend/app/models/__init__.py` — `GameSession`, `GameSessionStep` ORM models

### Frontend — Session UI
- `frontend/src/pages/GameSession.tsx` — session home page; Radarr notification (lines 410–422), Now Playing card (lines 329–394), tab view (line 439+)
- `frontend/src/pages/GameLobby.tsx` — session creation; Watch History tab (line 303) to be removed; tabs reduce to "Search Title" + "Import Chain"
- `frontend/src/pages/ArchivedSessions.tsx` — archived sessions list; delete action added here
- `frontend/src/components/NavBar.tsx` — Radarr notification banner mounts below this component
- `frontend/src/components/MovieFilterSidebar.tsx` — existing collapsible sidebar; refactored to persistent desktop sidebar
- `frontend/src/components/MovieCard.tsx` — existing card component; extended with MPAA, runtime, genre, TMDB rating fields
- `frontend/src/lib/api.ts` — `EligibleMovieDTO`, `GameSessionDTO`; new `/suggestions` endpoint type needed

### Planning State
- `.planning/ROADMAP.md` — Phase 4 success criteria and requirements (CACHE-01, CACHE-02, UX-06 through UX-09, SESSION-01, SESSION-02)
- `.planning/STATE.md` — architectural decisions from Phases 3, 03.1, 03.2

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `_prefetch_credits_background` + `_ensure_*` helpers in `game.py`: nightly cache job reuses these directly — fetch-and-cache pattern already established
- `MovieFilterSidebar.tsx`: existing filter sidebar component; refactor from collapsible-always to persistent-on-desktop
- `MovieCard.tsx`: shared card component used in lobby, eligible movies, and chain history — extend with new fields rather than creating a new component
- `EligibleMovieDTO` in `api.ts`: already has `poster_path`, `vote_average`, `genres`, `runtime`, `mpaa_rating`, `vote_count` from Phase 03.2 — no new DTO fields needed for card display
- `WatchEvent` model: genre affinity for suggestions computed from genres of WatchEvent-linked movies
- TMDB image pattern: `https://image.tmdb.org/t/p/w185{poster_path}` (upgrade from w92 used in grids — hero poster needs larger size)

### Established Patterns
- Radarr notification is currently state in `GameSession.tsx` (`radarrStatus` useState); refactor to a global/NavBar-level notification requires lifting state or using a context/event bus
- APScheduler: not yet in the codebase — new dependency; wire in `main.py` lifespan alongside existing TMDBClient setup
- Tailwind max-width: current layout uses `max-w-2xl` or similar narrow container; replace with `max-w-[1400px]` at the top layout wrapper
- Confirm dialogs: `window.confirm` used in GameSession for movie selection; Phase 4 destructive actions should use a proper modal (shadcn Dialog component already available)

### Integration Points
- Nightly cache job: new `CacheService` or inline scheduler task in `main.py`; reads `TMDB_CACHE_TOP_N` from settings; calls existing `_ensure_*` helpers per movie
- Suggestions endpoint: new `GET /sessions/{id}/suggestions` — queries eligible actors, fetches their movies, scores by genre affinity + rating, returns top 5
- Radarr notification: lift `radarrStatus` out of `GameSession.tsx` component state — needs to be accessible from NavBar level (React context or a lightweight notification store)
- Delete last step: new `DELETE /sessions/{id}/steps/last` — removes highest `step_order` step, resets session `current_movie_tmdb_id` and `current_movie_watched`
- Delete archived session: new `DELETE /sessions/{id}` — hard delete; only permitted when `status == "archived"`

</code_context>

<specifics>
## Specific Requirements

- Nightly cache: `TMDB_CACHE_TOP_N` and `TMDB_CACHE_TIME` must be documented in `.env.example`
- Radarr notification exact strings: `"Already in Radarr"` and `"Movie Queued for Download"` — no other variants
- Session home Now Playing card layout: poster (~120px wide) left-anchored, title + status text + CTA buttons to the right
- Movie cards: MPAA + runtime + genre + TMDB rating all visible without hover or expansion — always shown
- Filter sidebar: persistent on desktop (not collapsible), collapses to toggle button on mobile
- Suggestions tab: always shows exactly 5 movies; each card includes "via [Actor Name]" attribution
- Delete actions: use shadcn Dialog for confirmation (not `window.confirm`)
- App max-width: 1400px — apply at the root layout wrapper, not per-page

</specifics>

<deferred>
## Deferred Ideas

- Manual cache trigger via UI button or HTTP endpoint — user doesn't foresee needing it; schedule is sufficient
- Radarr download cancellation when deleting a session step — best-effort and complex; out of scope
- Movie suggestion count beyond 5 / pagination — fixed at 5 for all chain depths
- Cross-session suggestion history (avoid re-suggesting movies already picked in other sessions) — future enhancement
- Full-width no-cap layout — 1400px cap is the right balance for TV/desktop readability

</deferred>

---

*Phase: 04-caching-ui-ux-polish-and-session-management*
*Context gathered: 2026-03-17*
