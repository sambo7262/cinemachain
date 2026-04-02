# Phase 10: Query Mode — Context

**Gathered:** 2026-03-30
**Status:** Ready for research

<domain>
## Phase Boundary

Replace the `/search` placeholder (from Phase 9) with a fully functional Search page. Users can discover movies directly — by title, by person (actor/director), or by genre — without starting a game session. Results display in the same table layout as Game Mode's eligible movies. A movie splash gives full metadata and two action buttons: download via Radarr or mark as watched online.

No session context is required. No actor cards, no filmography views — results are always movies.

</domain>

<decisions>
## Implementation Decisions

### D-01: Search input modes

Single search box at the top of the Search page. Three input modes:

- **Default (no prefix) or `m:` prefix** → movie title search
- **`a:` prefix** → actor search — returns movies from that person's cast AND directing credits
- **`d:` prefix** → director search — identical behaviour to `a:` (same backend call, same results)

`a:` and `d:` are functionally equivalent — both return all movies where the named person has any credit (acting or directing). The distinction is a UI affordance only, not a backend split.

**Person name resolution:** take the top TMDB result. No disambiguation dialog — best-guess fuzzy match is sufficient for this use case.

**UI affordance:** the search box shows clear hint text and/or a label explaining the syntax (e.g. placeholder: `Search movies... or "a: Tom Hanks" for filmography`). A small syntax reference visible near the input so users don't need to remember prefixes.

### D-02: Results layout

Results are always movies, displayed in the same table layout as Game Mode's eligible movies list:

- **Columns:** poster thumbnail, title, year, TMDB rating, RT score, MPAA rating, genre, runtime
- **Sort:** same columns as Game Mode — rating, year, RT score, runtime (default: rating desc)
- **Filters:** reuse `MovieFilterSidebar` component — genre checkboxes, MPAA checkboxes, runtime range slider
- **Watched toggle:** toggle between "All" and "Unwatched Only" (filters on WatchEvent table)
- **RT scores:** enriched on the backend via the existing `fetch_rt_scores` / MDBList pattern

Actor/director search results show the same columns — runtime/rating/RT will be present for any movie already in DB cache; blank/null for uncached stubs.

### D-03: Genre browse (landing state)

Before any search is typed, the page shows a genre picker as the primary entry point:

- **Genre chips:** a row (or grid) of clickable genre buttons — e.g. Action, Comedy, Drama, Sci-Fi, Thriller, Horror, Animation, Documentary, Romance, Crime, etc.
- **Fixed genre list:** use a curated set of ~12–15 popular genres (not derived from DB at runtime)
- **On genre click:** fetch the top popular movies in that genre using TMDB Discover API (`/discover/movie?sort_by=popularity.desc&with_genres={genre_id}`) — culturally relevant, not just DB cache
- **Data source:** TMDB Discover is preferred; MDBList genre lists are a fallback to evaluate in research
- **Result count:** top 50 movies per genre, displayed in the same results table
- **Genre results are also sortable/filterable** like any other results

### D-04: Movie splash — action buttons

Reuse the existing movie splash dialog from Game Mode (poster, title, year, overview, rating, RT, MPAA, runtime, genres).

Replace game-specific action buttons with two Search-context buttons:

- **"Download via Radarr"** — calls the Radarr API to queue the movie for download; logs a WatchEvent record (source: `"radarr"`)
- **"Watch Online"** — no download triggered; logs a WatchEvent record (source: `"online"`) to track watch history for future statistics feature

Both buttons create a `WatchEvent` row. Neither requires a game session.

After either action: button shows a brief confirmation state (e.g. "Added" / "Marked"), then remains dismissible.

### D-05: Standalone Radarr request

"Download via Radarr" from Search must work without a session. This requires a new standalone endpoint (not session-scoped) that wraps the existing `_request_radarr` logic in `game.py`.

New endpoint: `POST /movies/{tmdb_id}/request` — queues movie via Radarr, returns status (`queued` / `already_in_radarr` / `not_found` / `error`).

The existing `PATCH /movies/{tmdb_id}/watched` endpoint handles the "Watch Online" WatchEvent write — reuse it (already exists).

### D-06: New backend endpoints required

| Endpoint | Purpose |
|----------|---------|
| `GET /search/movies?q=` | Enriched movie title search (RT, MPAA, runtime, genres — not just title/year/poster) |
| `GET /search/actors?q=` | Person name search → top TMDB person result → their full credits as movie list |
| `GET /movies/popular?genre=` | Top 50 popular movies by genre via TMDB Discover |
| `POST /movies/{tmdb_id}/request` | Standalone Radarr request (no session required) |

`PATCH /movies/{tmdb_id}/watched` already exists — reused for "Watch Online".

</decisions>

<code_context>
## Relevant Existing Code

### Frontend — reusable

**`SearchPlaceholder.tsx`** (`frontend/src/pages/SearchPlaceholder.tsx`)
- Current route handler at `/search` — full replacement target for this phase

**`MovieFilterSidebar.tsx`** (`frontend/src/components/MovieFilterSidebar.tsx`)
- Genre/MPAA/runtime filters — import and reuse directly; no changes needed
- `FilterState` and `DEFAULT_FILTER_STATE` exported from this file

**`MovieCard.tsx`** (`frontend/src/components/MovieCard.tsx`)
- Existing movie card — check if usable in results or if table rows are preferred

**Game Mode eligible movies table** (`frontend/src/pages/GameSession.tsx`)
- Full sort/filter/paginate/table pattern to port to Search page
- Sort columns: rating, year, RT, runtime, MPAA
- Watched toggle already wired to filter logic

### Backend — reusable / extendable

**`GET /movies/search?q=`** (`backend/app/routers/movies.py:23`)
- Exists but lightweight — returns only `tmdb_id, title, year, poster_path`
- Needs enrichment (RT, MPAA, runtime, genres) or a new richer endpoint alongside it

**`GET /actors/{tmdb_id}/filmography`** (`backend/app/routers/actors.py:15`)
- Returns full credits for a known TMDB actor ID
- Actor search by *name* does not yet exist — needs new `GET /search/actors?q=` endpoint
- TMDB `/search/person` → take top result → fetch their credits

**`_request_radarr(tmdb_id, radarr)`** (`backend/app/routers/game.py:1321`)
- Private helper — handles `movie_exists` check, `lookup_movie`, `add_movie`
- Extract to a shared service or expose via new standalone endpoint

**`PATCH /movies/{tmdb_id}/watched`** (`backend/app/routers/movies.py:190`)
- Already exists — logs WatchEvent with `source="manual"`; reuse for "Watch Online" (`source="online"`)

**`fetch_rt_scores`** (`backend/app/services/mdblist.py`)
- Used in `get_eligible_movies` to enrich RT scores in bulk
- Same pattern applies to Search results enrichment

### Data models

**`Movie`** — has `rt_score`, `mpaa_rating`, `overview`, `runtime`, `genres`, `vote_average`, `poster_path`
**`WatchEvent`** — has `tmdb_id`, `source`, `watched_at`; unique on `tmdb_id`
**`Actor`** / **`Credit`** — linked via Credit table; Credit has `character` field

### TMDB Discover API

`/discover/movie?sort_by=popularity.desc&with_genres={genre_id}&page=1` — returns up to 20 per page; fetch pages 1–3 for top ~50–60 popular movies per genre. Genre IDs are stable TMDB integers (e.g. Sci-Fi = 878, Action = 28).

</code_context>
