# Phase 10: Query Mode — Research

**Researched:** 2026-03-31
**Domain:** FastAPI endpoint authoring, React/TanStack Query page authoring, TMDB Discover API, Radarr standalone request
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**D-01: Search input modes**
Single search box. Three prefix modes: default/`m:` = title search, `a:` = actor/director credits search, `d:` = same as `a:`. Best-guess top TMDB person result — no disambiguation dialog.

**D-02: Results layout**
Same table as GameSession eligible movies. Columns: poster, title, year, TMDB rating, RT score, MPAA, genre, runtime. Sort: rating/year/RT/runtime (default: rating desc). Filters: reuse `MovieFilterSidebar`. Watched toggle: All / Unwatched Only. RT via existing `fetch_rt_scores` / MDBList pattern.

**D-03: Genre browse (landing state)**
Before any search: genre chips row/grid. ~12–15 curated genres. Genre click → TMDB Discover `popularity.desc` top 50 (3 pages × 20). Same table display.

**D-04: Movie splash — action buttons**
Reuse existing splash dialog. Replace game action buttons with: "Download via Radarr" (queues + WatchEvent `source="radarr"`) and "Watch Online" (WatchEvent `source="online"` only, no download). Both create WatchEvent. After action: confirmation state.

**D-05: Standalone Radarr request**
New endpoint: `POST /movies/{tmdb_id}/request` — no session required. Wraps `_request_radarr` logic from `game.py`. Returns `queued` / `already_in_radarr` / `not_found_in_radarr` / `error`.

**D-06: New backend endpoints**
| Endpoint | Purpose |
|----------|---------|
| `GET /search/movies?q=` | Enriched title search with RT, MPAA, runtime, genres |
| `GET /search/actors?q=` | Person name → top TMDB result → full credits as movie list |
| `GET /movies/popular?genre=` | Top 50 popular movies by genre via TMDB Discover |
| `POST /movies/{tmdb_id}/request` | Standalone Radarr request |

`PATCH /movies/{tmdb_id}/watched` reused for "Watch Online" (change source from `"manual"` to `"online"`).

### Claude's Discretion

None documented — all decisions are locked in CONTEXT.md.

### Deferred Ideas (OUT OF SCOPE)

- Person disambiguation dialogs
- Actor cards / filmography views
- Sonarr / TV show requests
- Stats dashboard
- Genre-constrained game mode
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| QMODE-01 | User can search movies by title and see results with poster, year, rating, genre, RT score | New `GET /search/movies?q=` endpoint; enrichment via `_ensure_movie_details_in_db` + `fetch_rt_scores`; same EligibleMovieDTO shape reused |
| QMODE-02 | User can search by actor name and browse their filmography | New `GET /search/actors?q=`; TMDB `/search/person` → top result → existing `fetch_actor_credits`; movie list uses same table |
| QMODE-03 | User can browse movies by genre | New `GET /movies/popular?genre=` via TMDB Discover; genre chips landing state; 3-page fetch (pages 1-3) = ~50-60 results |
| QMODE-04 | User can sort results by rating, year, runtime, RT score | Client-side sort reused from GameSession eligible movies pattern; same `sortCol`/`sortDir` state |
| QMODE-05 | User can toggle all movies / unwatched-only in results | `allMovies` toggle; WatchEvent join check client-side via `watched` flag on each movie DTO |
| QMODE-06 | User can request a movie from query results via Radarr | `POST /movies/{tmdb_id}/request`; calls `_request_radarr` helper; "Download via Radarr" button in splash |
</phase_requirements>

---

## Summary

Phase 10 replaces the `SearchPlaceholder.tsx` stub at `/search` with a fully functional Query Mode page. The implementation draws heavily on existing patterns: the eligible movies table from `GameSession.tsx`, the `MovieFilterSidebar` component, the `_request_radarr` helper in `game.py`, and the MDBList `fetch_rt_scores` enrichment service.

The primary backend work is four new endpoints in two new routers (or extended existing ones): `GET /search/movies`, `GET /search/actors`, `GET /movies/popular`, and `POST /movies/{tmdb_id}/request`. The person-name-to-credits flow is new but assembles existing primitives: TMDB `/search/person` → take index-0 result → call existing `fetch_actor_credits`. The Discover genre endpoint is new TMDB territory but straightforward (three paginated calls, stitch results).

The primary frontend work is a new `SearchPage.tsx` that reuses `MovieFilterSidebar`, ports the eligible movies table pattern, adds genre chips, and swaps the splash dialog action buttons for Download/Watch-Online. No new shared components are required — everything is contained in the new page with direct imports.

**Primary recommendation:** implement the four backend endpoints first (Wave 1), then build the frontend page top-to-bottom (Wave 2), then wire splash actions (Wave 3). The existing `EligibleMovieDTO` shape covers all required display fields — no new DTO needed for search results.

---

## Standard Stack

### Core (all already installed — no new packages required)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| FastAPI | existing | New router endpoints | Already used for all routes |
| SQLAlchemy async | existing | DB queries in new endpoints | Established async pattern throughout |
| httpx | existing | TMDB Discover API calls | Already used in TMDBClient |
| @tanstack/react-query | ^5.90.21 | Data fetching + cache | Established in all frontend pages |
| React | ^18.3.1 | Page component | Established |
| Tailwind CSS | ^3.4.19 | Styling | Established |
| lucide-react | ^0.577.0 | Icons | Established |
| shadcn/ui primitives | existing | Input, Button, Badge, Dialog | Already installed and used |

### No New Packages Required

All needed libraries are already in `package.json` and `requirements.txt`. The TMDBClient needs two new methods added (`search_person`, `discover_movies`), but no new HTTP library is required.

---

## Architecture Patterns

### Recommended Project Structure

```
backend/app/routers/
├── movies.py          # Add POST /{tmdb_id}/request and GET /popular?genre=
├── search.py          # NEW: GET /search/movies and GET /search/actors
└── game.py            # Extract _request_radarr to shared helper

backend/app/services/
└── tmdb.py            # Add search_person() and discover_movies() methods

frontend/src/pages/
├── SearchPage.tsx     # NEW: replaces SearchPlaceholder.tsx
└── SearchPlaceholder.tsx  # DELETED or replaced in-place

frontend/src/lib/
└── api.ts             # Add 4 new typed API call functions
```

### Pattern 1: New Search Router (`backend/app/routers/search.py`)

**What:** Separate router for search-scoped endpoints to keep `movies.py` focused on CRUD.
**When to use:** When adding a logical grouping of endpoints that aren't pure resource CRUD.

```python
# Source: FastAPI router registration pattern (matches existing main.py)
router = APIRouter(prefix="/search", tags=["search"])

@router.get("/movies")
async def search_movies_enriched(q: str, request: Request, db: AsyncSession = Depends(get_db)):
    ...

@router.get("/actors")
async def search_actors(q: str, request: Request, db: AsyncSession = Depends(get_db)):
    ...
```

Register in `main.py` alongside existing routers.

### Pattern 2: TMDB Discover — Three-Page Fetch

**What:** TMDB Discover returns 20 per page maximum. Fetch pages 1-3 in sequence (not parallel, to respect the semaphore) for ~50-60 movies.
**When to use:** `GET /movies/popular?genre=` endpoint.

```python
# Source: TMDB API docs — /discover/movie endpoint
TMDB_GENRE_IDS = {
    "Action": 28, "Adventure": 12, "Animation": 16, "Comedy": 35,
    "Crime": 80, "Documentary": 99, "Drama": 18, "Horror": 27,
    "Romance": 10749, "Science Fiction": 878, "Thriller": 53,
    "Fantasy": 14, "History": 36, "Music": 10402,
}

async def discover_movies(self, genre_id: int, page: int = 1) -> dict:
    async with self._sem:
        r = await self._client.get(
            "/discover/movie",
            params={"sort_by": "popularity.desc", "with_genres": genre_id, "page": page}
        )
        r.raise_for_status()
        return r.json()
```

Fetch pages 1, 2, 3 and combine `results` arrays before returning. Deduplicate by `tmdb_id`.

### Pattern 3: Person Name → Credits (Actor Search)

**What:** TMDB `/search/person?query=name` → take `results[0]` → call existing `fetch_actor_credits(person_id)` on the top result.

```python
# Source: TMDB API — /search/person endpoint
async def search_person(self, name: str) -> dict | None:
    async with self._sem:
        r = await self._client.get("/search/person", params={"query": name})
        r.raise_for_status()
        results = r.json().get("results", [])
        return results[0] if results else None
```

`GET /search/actors?q=name`:
1. Call `tmdb.search_person(q)` → get `person_id`
2. Call existing `fetch_actor_credits(person_id)` → get cast credits
3. Upsert movie stubs (same pattern as `actors.py` filmography endpoint)
4. Enrich: call `fetch_rt_scores` + `_ensure_movie_details_in_db` for RT/MPAA/runtime
5. Return movie list in same shape as other search endpoints

### Pattern 4: Enriched Movie Search (`GET /search/movies?q=`)

**What:** Enhances the existing lightweight `GET /movies/search?q=` with full metadata.

The existing endpoint returns only `tmdb_id, title, year, poster_path`. The new endpoint:
1. Calls TMDB `/search/movie` (same as existing)
2. For each result: upsert Movie stub in DB
3. Call `_ensure_movie_details_in_db(tmdb_ids, db, tmdb_client)` to hydrate `runtime`, `mpaa_rating`, `genres`, `overview`
4. Call `fetch_rt_scores(tmdb_ids, db)` to hydrate `rt_score`
5. Commit and return full Movie rows

**Key insight:** Reuse `_ensure_movie_details_in_db` exactly as it is used in `get_eligible_movies` in `game.py`. Don't reinvent this.

### Pattern 5: Standalone Radarr Request (`POST /movies/{tmdb_id}/request`)

**What:** Exposes `_request_radarr` from `game.py` without session context.

```python
# In backend/app/routers/movies.py — add after /poster-wall, before /{tmdb_id}
@router.post("/{tmdb_id}/request")
async def request_movie_standalone(
    tmdb_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    radarr: RadarrClient = request.app.state.radarr_client
    result = await _request_radarr(tmdb_id, radarr)
    return result
```

`_request_radarr` must be moved to a shared location (either `backend/app/services/radarr_helper.py` or imported from `game.py`). Simplest approach: import it from `game.py` in `movies.py` (avoid circular imports — verify `game.py` does not import from `movies.py`).

### Pattern 6: WatchEvent for "Watch Online"

**What:** Reuse `PATCH /movies/{tmdb_id}/watched` but the source field needs to support `"online"` (currently hardcoded to `"manual"`).

**Options:**
- Option A: Add `source` query param to existing endpoint — `PATCH /movies/{tmdb_id}/watched?source=online` — defaults to `"manual"` for backwards compat
- Option B: New endpoint `POST /movies/{tmdb_id}/watched-online`

**Recommendation:** Option A. One endpoint, backwards compatible, cleaner.

### Pattern 7: Frontend Query Mode Page

The page has three states:
1. **Landing (no query):** genre chips grid
2. **Loading:** spinner / loading message
3. **Results:** search box + sidebar filters + sort table

```
SearchPage state:
  searchInput: string          — raw input value
  debouncedSearch: string      — debounced for API calls
  searchMode: "title" | "person" | "genre"   — derived from prefix or chip click
  activeGenre: string | null
  results: SearchMovieDTO[]    — unified list
  sortCol / sortDir            — same as GameSession
  filters: FilterState         — from MovieFilterSidebar
  allMovies: boolean           — All / Unwatched Only toggle
  splashMovie: SearchMovieDTO | null
  splashOpen: boolean
  radarrStatus: string | null  — confirmation state after action
```

Prefix parsing (client-side, before debounce fires):
```typescript
function parseSearchMode(input: string): { mode: "title" | "person"; query: string } {
  if (input.startsWith("a:") || input.startsWith("d:")) {
    return { mode: "person", query: input.slice(2).trim() }
  }
  if (input.startsWith("m:")) {
    return { mode: "title", query: input.slice(2).trim() }
  }
  return { mode: "title", query: input.trim() }
}
```

### Pattern 8: Genre Chip Landing State

Fixed list of ~14 genres with TMDB genre IDs:

```typescript
const GENRE_CHIPS = [
  { label: "Action",        id: 28   },
  { label: "Adventure",     id: 12   },
  { label: "Animation",     id: 16   },
  { label: "Comedy",        id: 35   },
  { label: "Crime",         id: 80   },
  { label: "Documentary",   id: 99   },
  { label: "Drama",         id: 18   },
  { label: "Horror",        id: 27   },
  { label: "Romance",       id: 10749},
  { label: "Sci-Fi",        id: 878  },
  { label: "Thriller",      id: 53   },
  { label: "Fantasy",       id: 14   },
  { label: "History",       id: 36   },
  { label: "Music",         id: 10402},
] as const
```

On chip click: set `activeGenre` + fire `GET /movies/popular?genre={id}`. On any text typed in search box: clear `activeGenre`.

### Pattern 9: Splash Dialog Adaptation

Reuse exact structure from GameSession splash dialog. Replace the footer:

| GameSession Splash | SearchPage Splash |
|--------------------|-------------------|
| "Keep Browsing" cancel | "Close" cancel |
| Radarr checkbox + "Add to Session" | Two action buttons: "Download via Radarr" + "Watch Online" |

After either action button: set `radarrStatus` state → button shows confirmation text (e.g., "Added to Radarr" / "Marked as Watched") for 3 seconds, then resets. Dialog stays open so user can close manually. Match the `showRadarr` notification pattern from `NotificationContext` for the banner.

### Anti-Patterns to Avoid

- **Separate DTO type for search results:** The existing `EligibleMovieDTO` has all required fields (`tmdb_id`, `title`, `year`, `poster_path`, `vote_average`, `genres`, `runtime`, `watched`, `rt_score`, `mpaa_rating`, `overview`). Use it. Don't create `SearchMovieDTO` unless adding fields unique to search.
- **Re-implementing the sort/filter client logic:** Copy the sort/filter pattern from GameSession (the `useMemo` over `filteredMovies`). Don't rewrite it.
- **Calling TMDB Discover for every keystroke:** Genre browse is triggered only on chip click, not as a live search. Debounce is for title/actor text input only.
- **Creating a new WatchEvent source value that breaks the unique constraint:** `WatchEvent` has `UniqueConstraint("tmdb_id")` — only one WatchEvent per movie total. Both "Watch Online" and "Download via Radarr" must use `on_conflict_do_nothing`. A movie already in watch history won't create a duplicate.
- **Parallel TMDB Discover page fetches without semaphore:** Always use `self._sem` in TMDBClient methods. The semaphore limit is 10 concurrent.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| RT score enrichment for search results | Custom MDBList loop | `fetch_rt_scores(tmdb_ids, db)` from `mdblist.py` | Already handles 429, rate limiting, nulls, batch cap |
| Movie detail hydration (runtime, MPAA, genres) | Per-movie TMDB fetch loop | `_ensure_movie_details_in_db` from `game.py` | Handles cache miss, upserts, skips already-cached |
| Radarr add flow | Custom movie_exists + add | `_request_radarr(tmdb_id, radarr)` from `game.py` | Already handles lookup, add, `already_in_radarr`, error cases |
| Client-side sort with null stability | Custom comparator | Port exact two-pass null-stable pattern from `game.py` get_eligible_movies | Buggy tuple comparator mistake already made and fixed in Phase 4.3 |
| Genre/MPAA/runtime filter sidebar | New sidebar component | Import `MovieFilterSidebar` from `@/components/MovieFilterSidebar` | Complete, tested, exported |
| WatchEvent upsert | INSERT + check | `pg_insert().on_conflict_do_nothing()` | Already proven pattern in `movies.py` mark_movie_watched |

**Key insight:** All complex logic already exists in the codebase. This phase is assembly, not invention.

---

## Critical Implementation Details

### `_ensure_movie_details_in_db` Location

This function lives in `game.py` (not a shared service). It is a private async helper that fetches TMDB movie details and upserts `runtime`, `mpaa_rating`, `genres`, `overview`, `vote_count` into Movie rows.

To reuse it in the search router: either import it directly (check for circular imports first) or move it to a new `backend/app/services/movie_service.py`. Given it only calls `TMDBClient` and `AsyncSession`, moving it is safe and cleaner.

**Verify before implementing:** `game.py` imports from `movies.py` (via `from app.models import Movie`). `movies.py` currently does not import from `game.py`. So importing `_ensure_movie_details_in_db` from `game.py` in a new `search.py` router would create: `search.py → game.py` — no circular dependency. This is acceptable.

### WatchEvent Unique Constraint

`WatchEvent` has `UniqueConstraint("tmdb_id")` — one row per movie globally, regardless of source. The `source` field records how the movie was marked but doesn't affect uniqueness.

This means:
- If a movie is already watched, "Watch Online" silently no-ops (on_conflict_do_nothing) — correct behavior
- If a movie was watched via `"manual"` and user clicks "Watch Online", no duplicate created — correct
- The `source` in the new request should update existing row OR use the conflict-do-nothing approach — recommend `on_conflict_do_update(set_={"source": source_value})` to properly record the new source, but `do_nothing` is also acceptable since the watched state is what matters

For the `PATCH /movies/{tmdb_id}/watched` source param: safest is to add `source: str = "manual"` query param, validate it's in `("manual", "online", "radarr")`, pass through. Default `"manual"` preserves all existing callers.

### TMDB Discover: Route Registration Order Critical

`GET /movies/popular?genre=` must be registered before `GET /movies/{tmdb_id}` in `movies.py`. The existing code already has this problem documented: `"poster-wall" route declared before /{tmdb_id} catch-all"` (from STATE.md). FastAPI matches in declaration order; `popular` would be cast as integer and return 422 without this guard.

**Current order in movies.py:** `/search` → `/watched` → `/poster-wall` → `/{tmdb_id}` → `/{tmdb_id}/watched`

New endpoint `GET /movies/popular` must be inserted BEFORE `/{tmdb_id}`.

### Actor Filmography: Credit Direction

TMDB `/person/{id}/movie_credits` returns both `cast` (acting roles) and `crew` (directing, writing, etc.). The decision (D-01) says `a:` and `d:` both return movies where the person has "any credit (acting or directing)".

Implementation: combine `data.get("cast", [])` and `data.get("crew", [])` from the credits response, deduplicate by `tmdb_id`. Currently `fetch_actor_credits` only uses `cast`. The new `GET /search/actors` endpoint must handle both arrays.

Note: `GET /actors/{tmdb_id}/filmography` in `actors.py` only processes `cast` credits. The new search endpoint is different — it processes both. Do not modify the existing filmography endpoint.

### RT Score Enrichment: On-Demand vs Batch

`fetch_rt_scores` only fetches movies where `rt_score IS NULL` (skips already-cached). For search results that include recently-added movie stubs from TMDB, most will have `rt_score = None` initially. The enrichment call should be made after upserting movie stubs.

For genre browse (50 popular movies from TMDB Discover), many of those movies may already be in DB with RT scores. `fetch_rt_scores` will only fetch the uncached subset — efficient.

### Debounce Timing

Use the existing debounce pattern from GameSession:

```typescript
useEffect(() => {
  const t = setTimeout(() => setDebouncedSearch(searchInput), 300)
  return () => clearTimeout(t)
}, [searchInput])
```

Only fire API calls when `debouncedSearch.length >= 2` (avoid firing on single characters).

### `useQuery` Enabled Conditions

```typescript
// Title search — only when mode is "title" and query is non-empty
enabled: searchMode === "title" && debouncedSearch.length >= 2

// Actor/person search
enabled: searchMode === "person" && debouncedSearch.length >= 2

// Genre browse — on chip click (genre ID set), no text query
enabled: !!activeGenre && debouncedSearch.length === 0
```

Genre click should clear the text search input and vice versa.

---

## Common Pitfalls

### Pitfall 1: Route Ordering — `popular` vs `{tmdb_id}`

**What goes wrong:** `GET /movies/popular` returns 422 because FastAPI tries to cast `"popular"` as an integer for the `/{tmdb_id}` route.
**Why it happens:** FastAPI matches routes in declaration order. `/{tmdb_id}` has type `int`, so `"popular"` fails cast.
**How to avoid:** Register `GET /movies/popular` before `GET /movies/{tmdb_id}` in `movies.py`. Same principle as the existing `poster-wall` fix.
**Warning signs:** 422 Unprocessable Entity on GET /movies/popular.

### Pitfall 2: `_ensure_movie_details_in_db` N+1 TMDB Calls

**What goes wrong:** For 50 genre browse results, each with no cached details, the enrichment function makes 50 sequential TMDB API calls. On NAS with slow external connections, this can take 10-20 seconds.
**Why it happens:** The function fetches each movie individually via `fetch_movie(tmdb_id)` (which calls `append_to_response=credits`).
**How to avoid:** Accept this latency for now — it only happens once per movie (subsequent requests hit DB cache). Document the first-load latency in loading state. Consider capping enrichment to first 20 results if needed.
**Warning signs:** Genre browse first-load taking >10 seconds.

### Pitfall 3: WatchEvent Source Update vs No-Op

**What goes wrong:** User watches a movie via "Watch Online". Later requests via Radarr. The WatchEvent source stays "online" forever because `on_conflict_do_nothing` never updates it.
**Why it happens:** UniqueConstraint on `tmdb_id` means second write is silently dropped.
**How to avoid:** Use `on_conflict_do_update(set_={"source": ..., "watched_at": ...})` if source tracking matters. But per D-04, both buttons just need to create a WatchEvent — the exact source value is for future stats. `do_nothing` is acceptable for Phase 10.
**Warning signs:** Inconsistent source values in WatchEvent table (acceptable).

### Pitfall 4: `_request_radarr` Import Circular Dependency

**What goes wrong:** `search.py` imports `_request_radarr` from `game.py`. `game.py` imports from `app.models`, `app.db`, `app.services.*`. If any of those eventually import from `search.py`, circular import error at startup.
**Why it happens:** Python import system.
**How to avoid:** Check before importing. Safer path: move `_request_radarr` to `backend/app/services/radarr_helper.py` and import from there in both `game.py` and `movies.py`.
**Warning signs:** `ImportError: cannot import name '_request_radarr'` or circular import traceback at startup.

### Pitfall 5: Actor Credits Only Return `cast`, Missing `crew` for Directors

**What goes wrong:** `a: Christopher Nolan` returns no results because Nolan is primarily a director, not an actor — his credits are in `crew` not `cast`.
**Why it happens:** TMDB separates acting credits (`cast`) from directing/writing credits (`crew`).
**How to avoid:** In `GET /search/actors`, combine both `cast` and `crew` arrays from `/person/{id}/movie_credits`, then deduplicate by `tmdb_id`.
**Warning signs:** Person searches for known directors return empty results.

### Pitfall 6: Genre Browse Results Not Sorted by Rating (Default)

**What goes wrong:** TMDB Discover returns results sorted by `popularity.desc` (D-03 decision), but the table default sort is `rating desc` (D-02). The two don't match.
**Why it happens:** Backend returns TMDB popularity order; frontend default sort is rating.
**How to avoid:** This is correct behavior per decisions — backend returns discovery order, frontend immediately re-sorts to `rating desc`. The client-side sort handles this. The backend `GET /movies/popular` returns raw TMDB order; no server-side sort needed.
**Warning signs:** Genre results initially appear in popularity order rather than rating order — this is fixed once frontend sort applies.

### Pitfall 7: `radarr_client` Not Available in New Endpoints

**What goes wrong:** `POST /movies/{tmdb_id}/request` fails because `request.app.state.radarr_client` is None when Radarr is not configured.
**Why it happens:** `RadarrClient` is always initialized in `lifespan` but may have empty `base_url`/`api_key`. The client won't fail on init but will fail on actual API calls.
**How to avoid:** The existing `_request_radarr` helper already wraps all Radarr calls in `try/except` and returns `{"status": "error"}` on failure. No additional guard needed — it degrades gracefully.
**Warning signs:** `{"status": "error"}` returned on all Radarr requests when Radarr not configured.

---

## Code Examples

### New TMDBClient methods

```python
# Source: TMDB API documentation — /search/person, /discover/movie
# Add to backend/app/services/tmdb.py

async def search_person(self, name: str) -> dict | None:
    """Search TMDB for a person by name. Returns top result or None."""
    async with self._sem:
        r = await self._client.get("/search/person", params={"query": name})
        r.raise_for_status()
        results = r.json().get("results", [])
        return results[0] if results else None

async def discover_movies(self, genre_id: int, page: int = 1) -> list[dict]:
    """Fetch popular movies for a genre via TMDB Discover."""
    async with self._sem:
        r = await self._client.get(
            "/discover/movie",
            params={"sort_by": "popularity.desc", "with_genres": genre_id, "page": page},
        )
        r.raise_for_status()
        return r.json().get("results", [])
```

### Standalone Radarr endpoint

```python
# Source: existing _request_radarr pattern in game.py
# Add to backend/app/routers/movies.py (before /{tmdb_id} catch-all)

@router.post("/{tmdb_id}/request")
async def request_movie_standalone(
    tmdb_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """QMODE-06: Queue a movie via Radarr without a session."""
    from app.services.radarr_helper import request_radarr  # or import from game.py
    radarr: RadarrClient = request.app.state.radarr_client
    result = await request_radarr(tmdb_id, radarr)
    # Also log WatchEvent with source="radarr" if status is "queued"
    if result.get("status") == "queued":
        stmt = pg_insert(WatchEvent).values(
            tmdb_id=tmdb_id, movie_id=None, source="radarr",
            watched_at=datetime.utcnow(),
        ).on_conflict_do_nothing(index_elements=["tmdb_id"])
        await db.execute(stmt)
        await db.commit()
    return result
```

Note: per D-04, "Download via Radarr" also logs a WatchEvent. The endpoint handles both queue + WatchEvent creation in one call.

### Source param on PATCH /watched

```python
# Extend existing endpoint in movies.py
@router.patch("/{tmdb_id}/watched")
async def mark_movie_watched(
    tmdb_id: int,
    source: str = "manual",  # query param; "manual" | "online"
    db: AsyncSession = Depends(get_db),
):
    valid_sources = {"manual", "online"}
    if source not in valid_sources:
        source = "manual"
    stmt = pg_insert(WatchEvent).values(
        tmdb_id=tmdb_id, movie_id=None, source=source,
        watched_at=datetime.utcnow(),
    ).on_conflict_do_nothing(index_elements=["tmdb_id"])
    await db.execute(stmt)
    await db.commit()
    return {"tmdb_id": tmdb_id, "watched": True, "source": source}
```

### Frontend API additions (api.ts)

```typescript
// Add to api object in frontend/src/lib/api.ts

searchMovies: (q: string) =>
  apiFetch<EligibleMovieDTO[]>(`/search/movies?q=${encodeURIComponent(q)}`),

searchActors: (q: string) =>
  apiFetch<EligibleMovieDTO[]>(`/search/actors?q=${encodeURIComponent(q)}`),

getPopularByGenre: (genreId: number) =>
  apiFetch<EligibleMovieDTO[]>(`/movies/popular?genre=${genreId}`),

requestMovie: (tmdb_id: number) =>
  apiFetch<{ status: string }>(`/movies/${tmdb_id}/request`, { method: "POST" }),

markWatchedOnline: (tmdb_id: number) =>
  apiFetch<{ tmdb_id: number; watched: boolean; source: string }>(
    `/movies/${tmdb_id}/watched?source=online`,
    { method: "PATCH" }
  ),
```

Note: `requestMovie` already exists in `api.ts` for Game Mode (`api.requestMovie`). The standalone version should use a different name (e.g., `requestMovieStandalone`) to avoid collision. Check existing api.ts definitions.

### Client-side sort (port from GameSession)

```typescript
// Port exactly from GameSession.tsx filteredMovies useMemo
// sortCol: "rating" | "year" | "rt" | "runtime"
// sortDir: "asc" | "desc"
const sortedResults = useMemo(() => {
  return [...results].sort((a, b) => {
    // Two-pass null-stable sort (Phase 4.3 fix)
    let av: number | null = null
    let bv: number | null = null
    if (sortCol === "rating") { av = a.vote_average; bv = b.vote_average }
    else if (sortCol === "year") { av = a.year; bv = b.year }
    else if (sortCol === "rt") { av = a.rt_score; bv = b.rt_score }
    else if (sortCol === "runtime") { av = a.runtime; bv = b.runtime }
    const aN = av === null || av === undefined
    const bN = bv === null || bv === undefined
    if (aN && bN) return 0
    if (aN) return 1   // nulls always last
    if (bN) return -1
    return sortDir === "asc" ? av! - bv! : bv! - av!
  })
}, [results, sortCol, sortDir])
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Single sort column | Two-pass null-stable sort | Phase 4.3 | Nulls always sort last regardless of direction |
| Tuple comparator `(is_none, value)` | Explicit null guard + numeric sort | Phase 4.3 | Correct behavior under both asc and desc |
| `on_conflict_do_nothing` for all upserts | Same — still correct | Established | No change for Phase 10 |
| WatchEvent source `"manual"` hardcoded | Add `source` param | Phase 10 | Enables "online" and "radarr" source tracking |

---

## Open Questions

1. **`_request_radarr` extraction location**
   - What we know: it's a private function in `game.py`; it's needed in `movies.py` (new endpoint)
   - What's unclear: whether a circular import would result from importing `game.py` into a router that `main.py` loads alongside `game.py`
   - Recommendation: move to `backend/app/services/radarr_helper.py` during implementation. No risk; clean separation.

2. **`api.requestMovie` name collision in api.ts**
   - What we know: `api.requestMovie(sessionId, body)` already exists (takes `sessionId` as first arg)
   - What's unclear: whether naming the standalone version `requestMovieStandalone` vs a differently namespaced approach is cleaner
   - Recommendation: name it `requestMovieStandalone(tmdb_id)` to disambiguate clearly.

3. **Genre browse result count when many movies lack cached RT scores**
   - What we know: First-time genre browse for popular genres may trigger up to 50 MDBList API calls
   - What's unclear: whether the 10k/day quota is sufficient given concurrent usage
   - Recommendation: This is a home media app with a single user — 50 API calls per genre browse is well within quota. No throttling needed.

---

## Validation Architecture

Config has no `workflow.nyquist_validation` key — treat as enabled.

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest (backend) + vitest (frontend) |
| Config file | `backend/pytest.ini` or inline / `frontend/vite.config.ts` (test block exists) |
| Quick run command | `cd /path/to/backend && pytest tests/test_search.py -x` |
| Full suite command | `cd /path/to/backend && pytest` + `cd /path/to/frontend && npm test` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| QMODE-01 | `GET /search/movies?q=` returns enriched movie list | unit | `pytest tests/test_search.py::test_search_movies_enriched -x` | Wave 0 |
| QMODE-02 | `GET /search/actors?q=` returns actor filmography as movies | unit | `pytest tests/test_search.py::test_search_actors -x` | Wave 0 |
| QMODE-03 | `GET /movies/popular?genre=` returns top 50 popular movies | unit | `pytest tests/test_search.py::test_popular_by_genre -x` | Wave 0 |
| QMODE-04 | Frontend sort by rating/year/rt/runtime with null stability | unit | `npm test -- SearchPage` | Wave 0 |
| QMODE-05 | Unwatched-only toggle filters watched movies from results | unit | `npm test -- SearchPage` | Wave 0 |
| QMODE-06 | `POST /movies/{tmdb_id}/request` queues via Radarr + WatchEvent | unit | `pytest tests/test_search.py::test_request_movie_standalone -x` | Wave 0 |

### Sampling Rate

- **Per task commit:** `pytest tests/test_search.py -x` (backend) or `npm test -- --run SearchPage` (frontend)
- **Per wave merge:** `pytest` (full backend suite)
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `backend/tests/test_search.py` — new file covering QMODE-01 through QMODE-03 and QMODE-06 backend endpoints
- [ ] `frontend/src/pages/__tests__/SearchPage.test.tsx` — covers QMODE-04, QMODE-05 frontend behaviors

*(No new test infrastructure needed — pytest and vitest already configured)*

---

## Sources

### Primary (HIGH confidence)

- Direct code inspection of `backend/app/routers/movies.py`, `actors.py`, `game.py` — endpoint shapes, patterns, existing helpers
- Direct code inspection of `backend/app/services/tmdb.py` — TMDBClient methods, semaphore pattern
- Direct code inspection of `backend/app/services/mdblist.py` — `fetch_rt_scores` signature and behavior
- Direct code inspection of `backend/app/models/__init__.py` — Movie, WatchEvent, Actor, Credit schema
- Direct code inspection of `frontend/src/pages/GameSession.tsx` — table pattern, sort logic, splash dialog
- Direct code inspection of `frontend/src/components/MovieFilterSidebar.tsx` — exported interface
- Direct code inspection of `frontend/src/lib/api.ts` — existing API calls, DTO types
- Direct code inspection of `.planning/phases/10-query-mode/10-CONTEXT.md` — locked decisions

### Secondary (MEDIUM confidence)

- TMDB API genre IDs (stable integers, documented): Action=28, Adventure=12, Animation=16, Comedy=35, Crime=80, Documentary=99, Drama=18, Horror=27, Romance=10749, Sci-Fi=878, Thriller=53, Fantasy=14, History=36, Music=10402 — verified against known TMDB documentation, stable since TMDB v3 API launch
- TMDB Discover endpoint `sort_by=popularity.desc&with_genres={id}&page=N` — confirmed format from D-03 context notes and standard TMDB API usage

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries already in the project, no new dependencies
- Architecture: HIGH — endpoints map directly to existing code patterns; no novel design needed
- Pitfalls: HIGH — most derived from actual bugs already encountered in this codebase (Phase 4.3 null-sort fix, route ordering fix, circular import awareness)
- TMDB genre IDs: MEDIUM — stable integers but not re-verified via live API call; confirmed via documentation knowledge

**Research date:** 2026-03-31
**Valid until:** 2026-04-30 (stable domain — no breaking changes expected in FastAPI, React Query, or TMDB API within 30 days)
