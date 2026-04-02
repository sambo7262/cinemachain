# Phase 13: MDBList Expansion — Research

**Researched:** 2026-03-31
**Domain:** MDBList API, React SVG icons, SQLAlchemy Alembic migrations, FastAPI background jobs
**Confidence:** HIGH (core API sources confirmed via Kometa codebase; icon inventory confirmed via simple-icons repo)

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Decision 1: Ratings Badge Strip (MDBLIST-02)**
Replace the single `🍅 RT%` inline text with a flex-wrap badge strip. Each badge = SVG icon + score in natural format.

| Source | Display | Natural format | Example |
|--------|---------|----------------|---------|
| IMDB | SVG logo | decimal (1–10) | 7.8 |
| RT Tomatometer | Tomato SVG | percentage | 94% |
| RT Audience | Popcorn bucket SVG | percentage | 87% |
| Metacritic | MC logo SVG | percentage | 81% |
| MDB Average | MDB logo SVG | decimal (1–10) | 7.4 |
| TMDB | TMDB logo SVG | decimal (1–10) | 7.6 |
| Letterboxd | LB logo SVG | decimal (0–5) | 3.9 |

- **Eligible movie cards:** 4 badges — IMDB, RT Tomatometer, RT Audience, Metacritic
- **Splash dialog (all contexts):** All 7 badges
- **Now Playing tile:** IMDB + Tomatometer at minimum
- **SearchPage results + splash:** Same rules as GameSession equivalents
- Missing score: hidden entirely (no badge rendered)
- SVG logos first; fall back to styled text abbreviation if visually off

**Decision 2: Additional High-Value Data (MDBLIST-03)**
- Store `imdb_id` (tt-identifier) as new column on Movie model
- Replace all 4 TMDB external links with IMDB links (fallback to TMDB if null):
  1. `GameSession.tsx:1079` — eligible movie card link
  2. `GameSession.tsx:1224` — splash dialog link
  3. `SearchPage.tsx:555` — search page splash link
  4. `ChainHistory.tsx:89` — chain history movie link
- Actor external links (`ChainHistory.tsx:129`) unchanged

**Decision 3: Backfill & Quota Management**
- New Movie columns (nullable): `imdb_id`, `imdb_rating`, `metacritic_score`, `letterboxd_score`, `mdb_avg_score`
- Migration reset: set `rt_score = NULL` for all rows so backfill re-fetches all
- Settings table quota keys: `mdblist_calls_today` (int), `mdblist_calls_reset_date` (date)
- On-demand backfill in Settings: confirm dialog → POST `/mdblist/backfill/start` → poll GET `/mdblist/backfill/status` every 2s
- Status response shape: `{ running: bool, fetched: int, total: int, calls_used_today: int, daily_limit: int }`
- Nightly backfill (`backfill_rt_scores`) renamed/extended to `backfill_mdblist_scores`; trigger condition is any new field NULL
- Rate: `asyncio.sleep(0.1)` (~10 req/s)

### Claude's Discretion
- Icon fallback implementation details (text abbreviation style) if SVG looks visually off
- Exact router location for new endpoints (new `mdblist.py` router vs extending `settings.py`)
- In-memory vs DB state for in-flight backfill job tracking

### Deferred Ideas (OUT OF SCOPE)
- MDBList recommendations → Suggested Movies tab
- Watched list sync to MDBList
- MDBList vs TMDB fallback/redundancy
- IMDB actor links (Phase 16)
- Tier upgrade evaluation (document limits, but no implementation)
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| MDBLIST-01 | Research what MDBList basic tier (10k/day) provides beyond RT scores | MDBList API surface documented: 9 rating sources, `imdbid`, `score_average`; rate limits confirmed |
| MDBLIST-02 | IMDB ratings displayed alongside RT scores in eligible movies table, splash, and Now Playing tile | Source keys confirmed (`imdb`, `tomatoes`, `tomatoesaudience`, `metacritic`, `letterboxd`, `tmdb`); icon availability researched |
| MDBLIST-03 | Additional high-value MDBList data surfaced where contextually appropriate | `imdb_id` column + IMDB external link replacement; `mdb_avg_score` (`score_average`); backfill machinery |
</phase_requirements>

---

## Summary

MDBList's movie lookup API (`GET https://mdblist.com/api/?apikey=KEY&tm=TMDB_ID`) already returns all the rating sources the app needs. The existing `mdblist.py` service parses only `tomatoes` and `tomatoesaudience` from the `ratings` array; Phase 13 extends that to capture all sources. The complete ratings array also contains `imdb`, `metacritic`, `letterboxd`, `tmdb`, and `mdb` — all confirmed via the Kometa codebase which parses this exact API. The top-level `imdbid` field gives the IMDB tt-identifier at no extra API cost.

For SVG icons, Simple Icons (via `@icons-pack/react-simple-icons`) provides confirmed icons for IMDb (`SiImdb`), Letterboxd (`SiLetterboxd`), and The Movie Database (`SiThemoviedatabase`). Rotten Tomatoes, Metacritic, and MDBList are **not** in the Simple Icons set — these three require inline SVG paths or text abbreviations. The CONTEXT.md fallback strategy ("styled text abbreviation") is the right approach for RT and Metacritic; custom small SVGs are also viable.

The migration pattern is well established from `0008_rt_scores.py`. The new migration (0011) adds five nullable columns to `movies` and issues an `UPDATE movies SET rt_score = NULL` to force full re-fetch. Backfill job state should live in-memory as a module-level dict (simple, single-user NAS — no persistence needed for job tracking). Quota counters go in `app_settings` table via the existing `settings_service`.

**Primary recommendation:** Build a `RatingsBadge` component that accepts a `ratings` dict and renders only non-null badges. Feed it from an extended `EligibleMovieDTO` with explicit fields for all 7 rating values. Keep badge rendering logic isolated — it will be reused across 4+ locations.

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `@icons-pack/react-simple-icons` | 13.13.0 (latest) | SVG brand icons for IMDb, Letterboxd, TMDB | Official React wrapper for Simple Icons; tree-shakeable named exports |
| `simple-icons` | 16.14.0 (latest) | Raw SVG path data if inline custom SVG needed | Source of truth for all SI icons |
| `httpx` | already in project | MDBList HTTP requests | Already used in mdblist.py |
| `alembic` | already in project | DB migration | Established pattern in project |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `asyncio` | stdlib | Rate limiting sleep between MDBList calls | Already used in backfill |
| `sqlalchemy` | already in project | ORM column additions | Movie model extension |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `@icons-pack/react-simple-icons` | `react-icons/si` | react-icons bundles all SI icons non-tree-shakeably; @icons-pack is purpose-built and ships individual named components |
| Inline `<svg>` for RT/Metacritic | Unicode emoji fallback | Emoji are cross-platform but look inconsistent; styled text `RT` `MC` in badge is cleaner |
| In-memory job state | Redis / DB polling | For a single-user NAS app, in-memory dict in the mdblist module is simpler and sufficient |

**Installation:**
```bash
# Frontend only
cd frontend && npm install @icons-pack/react-simple-icons
```

**Version verification (confirmed 2026-03-31):**
- `@icons-pack/react-simple-icons`: 13.13.0
- `simple-icons`: 16.14.0

---

## Architecture Patterns

### Recommended Project Structure additions
```
backend/app/
├── routers/mdblist.py          # NEW: backfill endpoints (start/status)
├── services/mdblist.py         # EXTENDED: parse all rating sources
alembic/versions/
└── 20260331_0011_mdblist_expansion.py   # NEW migration

frontend/src/
├── components/RatingsBadge.tsx  # NEW: shared ratings badge strip
├── pages/GameSession.tsx        # MODIFIED: use RatingsBadge
├── pages/SearchPage.tsx         # MODIFIED: use RatingsBadge
├── components/ChainHistory.tsx  # MODIFIED: IMDB link swap
└── pages/Settings.tsx           # MODIFIED: backfill trigger UI
```

### Pattern 1: RatingsBadge Component
**What:** A reusable component that takes a ratings prop dict and renders flex-wrap badges with SVG icon + score. Only renders badges where value is non-null.
**When to use:** Every location displaying movie ratings (card, splash, now-playing tile)
**Example:**
```typescript
// frontend/src/components/RatingsBadge.tsx
import { SiImdb, SiLetterboxd, SiThemoviedatabase } from "@icons-pack/react-simple-icons"

interface MovieRatings {
  imdb_rating?: number | null      // e.g. 7.8 → displays "7.8"
  rt_score?: number | null          // e.g. 94 → displays "94%"
  rt_audience_score?: number | null // e.g. 87 → displays "87%"
  metacritic_score?: number | null  // e.g. 81 → displays "81%"
  mdb_avg_score?: number | null     // e.g. 7.4 → displays "7.4"
  vote_average?: number | null      // TMDB: e.g. 7.6 → displays "7.6"
  letterboxd_score?: number | null  // e.g. 3.9 → displays "3.9"
}

// variant controls which subset to show
type BadgeVariant = "card" | "splash" | "tile"
// card: imdb, rt, audience, metacritic (4)
// splash: all 7
// tile: imdb + rt (2)
```

### Pattern 2: Extended EligibleMovieDTO + Movie model
**What:** Add rating fields to the Movie SQLAlchemy model, the backend Pydantic DTO, and the frontend TypeScript interface.
**When to use:** Any time a new DB column needs to surface in the frontend
**Example:**
```python
# backend: Movie model additions
imdb_id: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
imdb_rating: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
metacritic_score: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
letterboxd_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
mdb_avg_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
# vote_average already exists — used as TMDB score; no new column needed
```

```typescript
// frontend: EligibleMovieDTO additions
imdb_id: string | null
imdb_rating: number | null
rt_audience_score: number | null   // add — currently missing from DTO
metacritic_score: number | null
letterboxd_score: number | null
mdb_avg_score: number | null
// vote_average already exists → used as tmdb_score badge
```

### Pattern 3: In-memory backfill job state
**What:** Module-level dict in `mdblist.py` (or new `mdblist` router) tracks running job state.
**When to use:** Single-user NAS, no persistence needed for transient job state.
**Example:**
```python
# backend/app/routers/mdblist.py
from dataclasses import dataclass, field
import asyncio
from typing import ClassVar

@dataclass
class _BackfillState:
    running: bool = False
    fetched: int = 0
    total: int = 0
    calls_used_today: int = 0
    daily_limit: int = 10_000
    _lock: ClassVar = asyncio.Lock()

_state = _BackfillState()

@router.post("/mdblist/backfill/start")
async def start_backfill(background_tasks: BackgroundTasks, db: AsyncSession = Depends(get_db)):
    if _state.running:
        raise HTTPException(409, "Backfill already running")
    background_tasks.add_task(_run_backfill, db_factory)
    return {"started": True}

@router.get("/mdblist/backfill/status")
async def backfill_status():
    return _state  # Pydantic serialises it
```

### Pattern 4: Quota counter in app_settings
**What:** Store `mdblist_calls_today` (str int) and `mdblist_calls_reset_date` (str date YYYY-MM-DD) in the existing `app_settings` table via `settings_service.save_settings()`.
**When to use:** Lightweight persistent counter; no new table needed.
**Example:**
```python
async def _increment_quota(db: AsyncSession) -> None:
    today_str = date.today().isoformat()
    reset_date = await settings_service.get_setting(db, "mdblist_calls_reset_date")
    if reset_date != today_str:
        await settings_service.save_settings(db, {
            "mdblist_calls_today": "0",
            "mdblist_calls_reset_date": today_str,
        })
    count_str = await settings_service.get_setting(db, "mdblist_calls_today") or "0"
    await settings_service.save_settings(db, {"mdblist_calls_today": str(int(count_str) + 1)})
```

### Anti-Patterns to Avoid
- **Sentinel 0 for new fields:** The existing `rt_score = 0` sentinel means "fetched, no data". Apply the same pattern to all new rating fields. Never store Python `None` for "fetched but absent" — use `0` or a negative sentinel consistently. The NULL-vs-0 distinction is load-bearing in the fetch skip logic.
- **Fetching new rating fields in a separate API call per source:** MDBList returns all sources in a single response. Extract all values in one pass per movie.
- **Rendering badge when value is 0:** The frontend must treat `0` and `null` identically as "hide badge" — same as the existing `rt_score != null && rt_score > 0` pattern.
- **Adding `imdb_id` to encryption:** `imdb_id` is not a secret; `_is_secret_key("imdb_id")` would return False (no "key"/"token"/"password" substring). Confirm no accidental encryption.

---

## MDBList API — Full Response Surface

### Confirmed Response Structure (HIGH confidence — source: Kometa codebase)

**Top-level fields:**
```json
{
  "title": "The Shawshank Redemption",
  "year": 1994,
  "type": "movie",
  "imdbid": "tt0111161",
  "tmdbid": 278,
  "traktid": 12345,
  "score": 96,
  "score_average": 9.6,
  "ratings": [...]
}
```

**Key top-level fields for Phase 13:**
| Field | Type | Notes |
|-------|------|-------|
| `imdbid` | string | IMDB tt-identifier, e.g. `"tt0111161"` |
| `score_average` | float | MDB composite average — the "MDB Average" badge (scale 0–10) |

**Ratings array — all confirmed source keys:**
| Source key | Value type | Scale | Display format | Badge label |
|------------|-----------|-------|----------------|-------------|
| `"imdb"` | float | 0–10 | `7.8` | IMDB |
| `"tomatoes"` | int | 0–100 | `94%` | RT Tomatometer |
| `"tomatoesaudience"` | int | 0–100 | `87%` | RT Audience |
| `"metacritic"` | int | 0–100 | `81%` | Metacritic |
| `"letterboxd"` | float | 0–5 | `3.9` | Letterboxd |
| `"tmdb"` | int | 0–100 | convert to 0–10 (divide by 10) OR store as-is and display raw | TMDB |
| `"mdb"` | float | unclear — use `score_average` at top level instead | — | use `score_average` |
| `"metacriticuser"` | float | 0–10 | n/a | deferred |
| `"trakt"` | int | 0–100 | n/a | deferred |
| `"myanimelist"` | float | 0–10 | n/a | deferred |

**Note on `"tmdb"` source in ratings array:** Kometa parses it as `Integer`. The TMDB vote_average is already stored as `vote_average` (float, 0–10) from TMDB directly. The `"tmdb"` source in MDBList ratings may be on a 0–100 scale. **Use `vote_average` from TMDB (already in DB) as the TMDB badge value** rather than parsing MDBList's `"tmdb"` source — avoids scale ambiguity.

**Note on `"tomatometr"` typo:** The existing `mdblist.py` checks for both `"tomatoes"` and `"tomatometr"` as aliases. Keep this dual-check in the extended parser.

### Rate Limits (MEDIUM confidence — free tier confirmed from official docs; paid tier inferred from project code)
| Tier | Requests/day | Source |
|------|-------------|--------|
| Free | 1,000 | Official docs (docs.mdblist.com) |
| Supporter/Paid | Configured as 10,000 in project code | `backend/app/services/mdblist.py` comment: "Cap per-request fetches — generous limit for paid tier (10k/day)" |

The project already operates on the assumption of 10k/day (paid tier). The `daily_limit` in the backfill status response should be `10_000` matching project assumption.

---

## SVG Icon Availability

### Simple Icons availability (HIGH confidence — confirmed via simple-icons GitHub repo icon listing)
| Service | Simple Icons slug | React component | Available |
|---------|-------------------|-----------------|-----------|
| IMDb | `imdb` | `SiImdb` | YES |
| Letterboxd | `letterboxd` | `SiLetterboxd` | YES |
| The Movie Database (TMDB) | `themoviedatabase` | `SiThemoviedatabase` | YES |
| Rotten Tomatoes | — | — | **NO** |
| Metacritic | — | — | **NO** |
| MDBList | — | — | **NO** |

### Icon strategy per badge
| Badge | Icon approach |
|-------|--------------|
| IMDB | `<SiImdb />` from `@icons-pack/react-simple-icons` |
| RT Tomatometer | Inline SVG tomato path OR text `🍅` emoji OR styled text `RT` |
| RT Audience | Inline SVG popcorn OR text `🍿` emoji OR styled text `Aud` |
| Metacritic | Styled text `MC` in badge |
| MDB Average | Styled text `MDB` in badge |
| TMDB | `<SiThemoviedatabase />` from `@icons-pack/react-simple-icons` |
| Letterboxd | `<SiLetterboxd />` from `@icons-pack/react-simple-icons` |

**Practical recommendation:** Use emoji for RT (🍅 tomatometer, 🍿 audience) as a deliberate stylistic choice — they are universally recognizable and the CONTEXT.md already uses `🍅`. For MC, MDB: small monospace text labels in the same badge style. This avoids adding custom SVG files to the project.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| SVG brand icons for IMDb/Letterboxd/TMDB | Custom SVG files | `@icons-pack/react-simple-icons` | Maintained, color correct, accessible |
| Alembic migration for new columns | Manual SQL ALTER TABLE | `op.add_column()` + `op.execute("UPDATE movies SET rt_score = NULL")` | Follows project pattern, reversible |
| Background job runner | Custom thread/process | FastAPI `BackgroundTasks` | Already in use in project (poster backfill, actor prefetch) |
| Quota reset detection | Cron or scheduler | Date comparison on each API call | Single-user NAS, no cron needed |

**Key insight:** All the hard infrastructure (async HTTP client, backfill loop, settings storage, background tasks) already exists. Phase 13 is primarily wiring existing pieces together plus parsing more fields from the already-fetched response.

---

## Common Pitfalls

### Pitfall 1: rt_score sentinel vs NULL ambiguity
**What goes wrong:** New columns added as NULL. After migration, `rt_score` is also reset to NULL. The backfill condition `Movie.rt_score.is_(None)` now picks up movies that previously had `rt_score = 0` (fetched, no data). This is intentional (want to re-fetch all), but the new fields (`imdb_rating`, etc.) must use the same sentinel pattern: store `0` when fetched but absent, `NULL` when never fetched. If you store Python `None` for "fetched, no data", the backfill will re-fetch that movie on every run.
**How to avoid:** In `_fetch_and_store_mdblist()`, for every new field: `movie.imdb_rating = value if value is not None else 0.0` (or `0`).
**Warning signs:** Movie count in backfill status never reaches zero between runs.

### Pitfall 2: Frontend badge shows for score = 0
**What goes wrong:** `movie.imdb_rating` is `0` (sentinel) and frontend renders `0.0` badge.
**How to avoid:** RatingsBadge renders only when `value != null && value > 0`. Mirror existing pattern: `movie.rt_score != null && movie.rt_score > 0`.

### Pitfall 3: `vote_average` vs MDBList `"tmdb"` source scale mismatch
**What goes wrong:** MDBList's `"tmdb"` rating source may be 0–100 (integer). `vote_average` is 0–10 (float from TMDB). If you replace `vote_average` with MDBList's `"tmdb"` you'd display `76` instead of `7.6`.
**How to avoid:** Do not parse the `"tmdb"` source from MDBList at all. Use the existing `vote_average` column as the TMDB badge value.

### Pitfall 4: `imdb_id` accidentally encrypted
**What goes wrong:** `settings_service._is_secret_key("imdb_id")` checks if "key" is a substring of the field name — `"imdb_id"` does NOT contain "key", so it will not be encrypted. However, if a future developer passes `imdb_id` through `save_settings()`, confirm behavior. This does not apply since `imdb_id` is a Movie column, not a settings key.
**How to avoid:** Keep `imdb_id` in the Movie model, not in app_settings.

### Pitfall 5: Concurrent backfill calls
**What goes wrong:** Two requests hit `POST /mdblist/backfill/start` simultaneously, spawning two background tasks.
**How to avoid:** Check `_state.running` before starting; return HTTP 409 if already running.

### Pitfall 6: BackgroundTasks DB session lifecycle
**What goes wrong:** FastAPI `BackgroundTasks` executes after response is sent. If the task receives a `db: AsyncSession` from `Depends(get_db)`, that session is closed before the task runs.
**How to avoid:** Use `_bg_session_factory` (already imported in `game.py`) to create a new session inside the background task, not the request-scoped one. Reference: `game.py` line 19 `from app.db import engine, get_db, _bg_session_factory`.

### Pitfall 7: `rt_audience_score` missing from EligibleMovieDTO
**What goes wrong:** `rt_audience_score` exists on the Movie model and is fetched, but the backend DTO and frontend `EligibleMovieDTO` don't include it. The RT Audience badge in the design requires this field.
**How to avoid:** Add `rt_audience_score` to the DTO serialization in `game.py`'s `movies_map` construction and to the frontend `EligibleMovieDTO` interface simultaneously.

---

## Existing RT Display Locations (exact lines to replace)

All 3 in `GameSession.tsx` and 1 in `SearchPage.tsx` confirmed via grep:

| Location | File | Line | Current pattern | Replace with |
|----------|------|------|----------------|--------------|
| Now Playing tile | `GameSession.tsx` | ~624 | `🍅 {rt_score}%` inline | `<RatingsBadge variant="tile" ratings={currentMovie} />` |
| Eligible movie card Row 4 | `GameSession.tsx` | ~1104 | `🍅 {rt_score}%` | `<RatingsBadge variant="card" ratings={movie} />` |
| Splash dialog stats row | `GameSession.tsx` | ~1199 | `🍅 ${splashMovie.rt_score}%` in Badge | `<RatingsBadge variant="splash" ratings={splashMovie} />` |
| SearchPage splash | `SearchPage.tsx` | ~537-538 | `{splashMovie.rt_score}% RT` in Badge | `<RatingsBadge variant="splash" ratings={splashMovie} />` |

SearchPage also has a table column at line ~451 (`{movie.rt_score != null ? ...}`) — needs updating to show IMDB + RT.

**TMDB external link replacements (all 4 confirmed):**

| Location | File | Line | Replace with |
|----------|------|------|--------------|
| Eligible movie card | `GameSession.tsx` | 1079 | `imdb_id ? imdb.com/title/${imdb_id} : themoviedb.org/movie/${tmdb_id}` |
| Splash dialog | `GameSession.tsx` | 1224 | same pattern |
| SearchPage splash | `SearchPage.tsx` | 555 | same pattern |
| ChainHistory movie | `ChainHistory.tsx` | 89 | same pattern |

---

## Code Examples

### Parsing all rating sources in mdblist.py
```python
# Source: Kometa mdblist.py + existing project mdblist.py
data = resp.json()
ratings = data.get("ratings", [])
imdbid = data.get("imdbid")          # "tt0111161" — store on movie.imdb_id
score_average = data.get("score_average")  # float 0–10 — store on movie.mdb_avg_score

tomatometer = audience = metacritic = letterboxd = imdb_rating = None
for r in ratings:
    src = r.get("source", "")
    val = r.get("value")
    if src in ("tomatoes", "tomatometr"):
        tomatometer = val
    elif src in ("tomatoesaudience", "tomatoesau"):
        audience = val
    elif src == "metacritic":
        metacritic = val
    elif src == "letterboxd":
        letterboxd = val
    elif src == "imdb":
        imdb_rating = val
    # "tmdb" source deliberately skipped — use vote_average from TMDB instead

movie.imdb_id = imdbid
movie.rt_score = tomatometer if tomatometer is not None else 0
movie.rt_audience_score = audience if audience is not None else 0
movie.imdb_rating = float(imdb_rating) if imdb_rating is not None else 0.0
movie.metacritic_score = int(metacritic) if metacritic is not None else 0
movie.letterboxd_score = float(letterboxd) if letterboxd is not None else 0.0
movie.mdb_avg_score = float(score_average) if score_average is not None else 0.0
```

### Alembic migration 0011
```python
# Source: pattern from 20260322_0008_rt_scores.py
revision = "0011"
down_revision = "0010"

def upgrade() -> None:
    op.add_column("movies", sa.Column("imdb_id", sa.String(20), nullable=True))
    op.add_column("movies", sa.Column("imdb_rating", sa.Float(), nullable=True))
    op.add_column("movies", sa.Column("metacritic_score", sa.Integer(), nullable=True))
    op.add_column("movies", sa.Column("letterboxd_score", sa.Float(), nullable=True))
    op.add_column("movies", sa.Column("mdb_avg_score", sa.Float(), nullable=True))
    # Reset rt_score to NULL so full backfill re-fetches and populates all new fields
    op.execute("UPDATE movies SET rt_score = NULL")

def downgrade() -> None:
    op.drop_column("movies", "mdb_avg_score")
    op.drop_column("movies", "letterboxd_score")
    op.drop_column("movies", "metacritic_score")
    op.drop_column("movies", "imdb_rating")
    op.drop_column("movies", "imdb_id")
```

### RatingsBadge React component (skeleton)
```typescript
// Source: pattern from CONTEXT.md decisions + existing badge usage in GameSession.tsx
import { SiImdb, SiLetterboxd, SiThemoviedatabase } from "@icons-pack/react-simple-icons"

interface RatingsProps {
  rt_score?: number | null
  rt_audience_score?: number | null
  imdb_rating?: number | null
  metacritic_score?: number | null
  mdb_avg_score?: number | null
  vote_average?: number | null
  letterboxd_score?: number | null
}

const BADGE_SETS = {
  card:   ["imdb", "rt", "audience", "metacritic"],
  splash: ["imdb", "rt", "audience", "metacritic", "mdb", "tmdb", "letterboxd"],
  tile:   ["imdb", "rt"],
}

export function RatingsBadge({ variant = "card", ...ratings }: RatingsProps & { variant?: keyof typeof BADGE_SETS }) {
  // Render only present (>0, non-null) badges in variant's set
  // Each badge: icon/label + formatted score
}
```

### IMDB external link with TMDB fallback
```typescript
// Source: CONTEXT.md Decision 2
const movieHref = movie.imdb_id
  ? `https://www.imdb.com/title/${movie.imdb_id}`
  : `https://www.themoviedb.org/movie/${movie.tmdb_id}`
const linkLabel = movie.imdb_id ? "View on IMDB" : "View on TMDB"
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Only RT scores from MDBList | All 7 rating sources from same API call | Phase 13 | No extra API cost; same request already returns all data |
| TMDB external links | IMDB external links (with TMDB fallback) | Phase 13 | More directly useful to users |
| `🍅 RT%` text inline | `RatingsBadge` component with icons | Phase 13 | Reusable, extensible for future sources |

**Existing behavior preserved:**
- `vote_average` (TMDB star rating) already displays in Now Playing tile and cards — keep this, it becomes the "TMDB" badge
- `rt_score` and `rt_audience_score` columns already exist — migration does not drop them

---

## Open Questions

1. **`tmdb_cache_top_actors` field in Settings**
   - What we know: it appears in `settings_service._ENV_KEYS_TO_MIGRATE` and backend `SettingsResponse`/`SettingsUpdateRequest`, but NOT in `Settings.tsx` form (the frontend form is missing it)
   - What's unclear: Is this intentional or an oversight from a prior phase?
   - Recommendation: Out of scope for Phase 13 — don't fix it here, but don't break it either

2. **`"tmdb"` source in MDBList ratings array — exact scale**
   - What we know: Kometa parses it as `Integer`; vote_average from TMDB is float 0–10
   - What's unclear: Whether MDBList `"tmdb"` source is 0–100 or 0–10
   - Recommendation: Skip parsing the `"tmdb"` key from MDBList entirely; use existing `vote_average` column for the TMDB badge

3. **`mdb` source key vs `score_average` top-level field**
   - What we know: `score_average` is confirmed at top-level; a `"mdb"` source may also exist in the ratings array (unclear exact key)
   - What's unclear: Whether `"mdb"` in ratings array duplicates `score_average`
   - Recommendation: Use top-level `score_average` for `mdb_avg_score`; do not rely on ratings array `"mdb"` key

---

## Validation Architecture

`workflow.nyquist_validation` is not set in `.planning/config.json` — treat as enabled.

### Test Framework
| Property | Value |
|----------|-------|
| Backend framework | pytest (asyncpg-skip pattern) |
| Frontend framework | vitest |
| Backend quick run | `cd backend && python -m pytest tests/test_mdblist.py -x` (Wave 0 creates this) |
| Backend full suite | `cd backend && python -m pytest tests/ -x` |
| Frontend quick run | `cd frontend && npm test -- --run` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| MDBLIST-01 | MDBList parser extracts all 6 new fields from mock API response | unit | `pytest tests/test_mdblist.py::test_parse_all_rating_sources -x` | Wave 0 gap |
| MDBLIST-01 | `score_average` top-level field stored as `mdb_avg_score` | unit | `pytest tests/test_mdblist.py::test_score_average_stored -x` | Wave 0 gap |
| MDBLIST-01 | `imdbid` top-level field stored as `imdb_id` | unit | `pytest tests/test_mdblist.py::test_imdbid_stored -x` | Wave 0 gap |
| MDBLIST-02 | Backfill status endpoint returns correct schema | unit | `pytest tests/test_mdblist.py::test_backfill_status_schema -x` | Wave 0 gap |
| MDBLIST-03 | RatingsBadge renders correct badges for `card` variant | unit (vitest) | `cd frontend && npm test -- --run` | Wave 0 gap |
| MDBLIST-03 | RatingsBadge hides badges when value is null or 0 | unit (vitest) | `cd frontend && npm test -- --run` | Wave 0 gap |

### Sampling Rate
- **Per task commit:** `cd backend && python -m pytest tests/test_mdblist.py -x`
- **Per wave merge:** `cd backend && python -m pytest tests/ -x && cd frontend && npm test -- --run`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `backend/tests/test_mdblist.py` — covers all MDBLIST-01/02/03 backend behaviors
- [ ] `frontend/src/components/__tests__/RatingsBadge.test.tsx` — covers badge render/hide logic

---

## Sources

### Primary (HIGH confidence)
- `github.com/Kometa-Team/Kometa/blob/master/modules/mdblist.py` — exact source key strings for all MDBList rating sources; value type handling per source
- `github.com/simple-icons/simple-icons/tree/develop/icons` — SVG file inventory confirming imdb.svg, letterboxd.svg, themoviedatabase.svg present; rottentomatoes.svg, metacritic.svg absent
- `/Users/Oreo/Projects/CinemaChain/backend/app/services/mdblist.py` — existing project implementation; `"tomatometr"` alias confirmed
- `/Users/Oreo/Projects/CinemaChain/backend/app/models/__init__.py` — current Movie columns; `vote_average` already exists
- `/Users/Oreo/Projects/CinemaChain/backend/alembic/versions/20260322_0008_rt_scores.py` — migration pattern reference

### Secondary (MEDIUM confidence)
- `docs.mdblist.com/docs/api` (web search result summary) — free tier: 1,000 req/day confirmed
- `github.com/linaspurinis/api.mdblist.com` — official API docs repo; `imdbid` and `score_average` top-level fields confirmed in search result summaries
- `@icons-pack/react-simple-icons` v13.13.0 / `simple-icons` v16.14.0 — npm registry confirmed via `npm view`

### Tertiary (LOW confidence)
- Project comment in `mdblist.py` "generous limit for paid tier (10k/day)" — supporter tier limit inferred, not independently verified from docs

---

## Metadata

**Confidence breakdown:**
- MDBList API source keys: HIGH — confirmed via Kometa production codebase that actively parses the same endpoint
- Simple Icons availability: HIGH — confirmed via direct simple-icons GitHub icon file listing
- Rate limits (free 1k): MEDIUM — confirmed in official docs search results
- Rate limits (paid 10k): LOW — inferred from project comment only
- Migration pattern: HIGH — exact pattern used in 3 prior migrations in this project
- Background job pattern: HIGH — BackgroundTasks + `_bg_session_factory` pattern already used in `game.py`

**Research date:** 2026-03-31
**Valid until:** 2026-04-30 (MDBList API is stable; Simple Icons adds icons monthly but removals are rare)
