# Phase 15 Context — MDBList Suggested Movies

**Phase goal:** Surface TMDB-recommended movies as a Suggested filter in the eligible movies panel — cross-referenced against eligible actors so every suggestion is playable at the current game step.
**Requirements:** SUGGEST-01, SUGGEST-02, SUGGEST-03

---

## Decision 1: Recommendations Engine (SUGGEST-01)

### Source
**TMDB `/movie/{id}/recommendations`** — already authenticated via stored TMDB API key, no new credentials needed. Returns ~20 suggested movies per seed movie. MDBList has no recommendation endpoint — it's ratings-only.

### Seed pool — sliding window
- Seed = last N watched movies from `watch_events` ordered by watched time descending
- N is **user-configurable in Settings** (default: 5)
- After each new watch, the window advances: oldest seed drops off, newest watched movie enters
- Example: N=5, after watching movie 6 → seeds are movies 2–6 (movie 1 drops)

### Ranking
Suggestions are ranked by **frequency** — how many seed movies independently recommended the same title. A movie recommended by 3 of 5 seeds ranks above one recommended by 1. Ties can be left in any stable order.

### Per-movie caching
Store TMDB recommendations on the `Movie` row as a new **`tmdb_recommendations` JSON column** (list of TMDB IDs, ~20 items). This reduces sliding window cost to **1 TMDB call per newly watched movie** — the other N-1 seeds are read from cached DB columns.

- If a Movie row already has `tmdb_recommendations` populated (from a previous session), no API call is made for that seed.
- First session ever: up to N calls to warm the cache. Each movie thereafter: 1 call.

### Fetch trigger
Fired as a **fire-and-forget background task** when `mark_current_watched` is called (game mode) — same BackgroundTasks pattern as Phase 14 MDBList push. The response to the frontend is not blocked. Results are ready when the eligible movies panel opens for the next actor step.

---

## Decision 2: UI Placement (SUGGEST-02)

### Filter toggle — not a tab
"Suggested" is a **filter toggle button** in the eligible movies panel, alongside the existing Saved (★) and Shortlist (✓) controls. It is **not** a new top-level tab.

Filter bar layout:
```
All Movies | Unwatched Only | ★ Saved | ✓ Shortlist | ✦ Suggested
```

### Strict filter
When "Suggested" is active, the list shows **only** the intersection of TMDB recommendations and the current eligible pool. Same behaviour as Saved and Shortlist filters — no pinning or mixing with non-suggested movies.

### Hidden when empty
If no TMDB suggestions intersect the eligible pool, the Suggested toggle is **not rendered** — no empty state, no disabled button.

### Data and actions
Suggested movies use the same `EligibleMovieResponse` DTO and render identically to regular eligible movies: poster, title, year, runtime, MPAA, RatingsBadge, IMDB link, save (★), shortlist (✓), select to pick.

---

## Decision 3: Intersection Rule (SUGGEST-03)

### Validity check
A TMDB-suggested movie is valid (included in the filter) if and only if it appears in the **full eligible movies pool for the current step** — i.e. it is reachable via at least one actor who has not yet been used in the chain.

This reuses the existing `get_eligible_movies` logic (combined view, `actor_id=None`, chain-history enforced). No separate intersection query needed — just cross-reference the TMDB recommendation IDs against the eligible pool.

### Reused actors excluded
Actors already used in the session chain cannot drive eligibility. A suggested movie is only valid if the shared actor connecting it to the current step is not in the chain history. This is automatically enforced by the existing eligibility query.

---

## Decision 4: Settings (N configuration)

### New settings field: tmdb_suggestions_seed_count
- Stored in `app_settings` as `tmdb_suggestions_seed_count` (integer)
- Default: `5`
- Exposed in Settings page under a new "Suggested Movies" section (or alongside existing TMDB settings)
- Label: "Recommendation seed depth" or "Movies to seed suggestions (last N watched)"
- No live validation — takes effect on next `mark_current_watched` fire

---

## Deferred Ideas (captured, not in scope for Phase 15)

- **Phase 14 MDBList sync removal** — All watched-list push code (fire-and-forget in game.py/movies.py, `/watched-sync` endpoints, Settings UI, `mdblist_synced_at` column) to be removed in the upcoming **Watched History** phase. The MDBList list sync no longer has a purpose since recommendations come from TMDB.
- **Watched History view** — New 3rd nav section (Game / Query / Watched) showing all watched movies across sessions in a tile/grid format with toggle and search. Replaces the MDBList watched list concept entirely.
- **Actor-scoped suggestions** — Currently suggestions are cross-referenced against any eligible actor. A future option: show which actor makes each suggestion reachable. Not in scope.

---

## Code Context

### New DB column
- `Movie.tmdb_recommendations: list[int] | None` — JSON-encoded list of TMDB IDs; nullable (NULL = not yet fetched)
- New Alembic migration required

### TMDB API call
- Endpoint: `GET https://api.themoviedb.org/3/movie/{tmdb_id}/recommendations`
- Auth: existing `tmdb_api_key` from `app_settings`
- Response: `results[]` array, each has `id` (TMDB ID); take top 20
- Researcher must confirm: pagination needed? Rate limits?

### Fetch + cache function (new, in `tmdb.py` service or new `suggestions.py`)
```python
async def fetch_and_cache_recommendations(tmdb_id: int, db: AsyncSession) -> list[int]:
    # 1. Check Movie.tmdb_recommendations — return if already populated
    # 2. Call TMDB /movie/{tmdb_id}/recommendations
    # 3. Store result on Movie row
    # 4. Return list of recommended tmdb_ids
```

### Aggregation function (new)
```python
async def get_session_suggestions(session_id: int, db: AsyncSession, n: int = 5) -> list[int]:
    # 1. Fetch last N watch_events for any session (global sliding window)
    # 2. For each, call fetch_and_cache_recommendations (cache hit = no API call)
    # 3. Count frequency per tmdb_id across all seed results
    # 4. Return sorted by frequency desc
```

### Background task wiring
- `backend/app/routers/game.py` — `mark_current_watched()` already accepts `BackgroundTasks`
- Add: `background_tasks.add_task(update_session_suggestions, session_id, db_factory)`
- This fires fetch_and_cache for the newly watched movie, then updates session suggestion cache

### Frontend
- `frontend/src/pages/GameSession.tsx` — add "Suggested" filter toggle alongside Saved/Shortlist
- `frontend/src/lib/api.ts` — new `getSessionSuggestions(sessionId)` function
- Suggested filter queries eligible movies cross-referenced against suggestion IDs
- Toggle hidden when `suggestions.length === 0`

### Settings
- `backend/app/routers/settings.py` — add `tmdb_suggestions_seed_count: int = 5` to `SettingsResponse` + `SettingsUpdateRequest`
- `frontend/src/pages/Settings.tsx` — add seed count input in TMDB or new Suggestions section
