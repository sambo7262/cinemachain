# Phase 6: New Features - Research

**Researched:** 2026-03-22
**Domain:** FastAPI + React/TypeScript feature additions to CinemaChain
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

#### Item 1 — TMDB Actor Name in Chain (CSV Import Override)
- D-01: Affects only the CSV import path where a raw TMDB ID is entered as an actor override
- D-02: If the actor name is not stored locally, query TMDB to resolve it before displaying in the chain history
- D-03: Display the resolved actor name everywhere the chain step is shown (chain history table, session steps)

#### Item 2 — Movie Selection Splash Window
- D-04: Fully replaces the current simple confirmation dialog — no fallback to the old dialog
- D-05: Splash displays: movie poster, title, TMDB rating, MPAA rating, runtime, and full TMDB `overview` field (no truncation)
- D-06: Splash includes a Radarr checkbox, selected by default
- D-07: If Radarr checkbox is checked → session advances AND Radarr download request is sent
- D-08: If Radarr checkbox is unchecked → session still advances but NO Radarr request is made
- D-09: Splash is triggered when user selects an unwatched movie from the Eligible Movies panel

#### Item 3 — Session Settings Menu Consolidation
- D-10: Existing session dropdown gains two new items: "Archive Session" and "Edit Session Name"
- D-11: "Archive Session" moves from home page session card to this menu only — remove archive button from home page entirely
- D-12: "Archive Session" requires a confirmation dialog before executing
- D-13: "Edit Session Name" opens a modal with a text field pre-populated with the current session name

#### Item 4 — Chain History Search
- D-14: A search input is added above the chain history table
- D-15: Filters in real-time as the user types — non-matching rows are hidden
- D-16: Searches both movie names AND actor names simultaneously

#### Item 5 — TMDB External Links
- D-17: Every movie and actor that has a TMDB ID gets a link to their TMDB page
- D-18: Links open in a new browser tab
- D-19: Link surfaces: Eligible Movies table, Chain History table, new Movie Selection Splash
- D-20: NOT added to the Eligible Actors grid (not in scope)

#### Item 6 — In-App Settings / Config Page
- D-21: A new Settings page is added to the app
- D-22: On first launch (or if TMDB credentials are absent), a full blocking onboarding screen is shown
- D-23: TMDB API key and base URL are the only required values
- D-24: On first launch, if a `.env` file exists, its values are read and used to pre-populate settings automatically (one-time migration)
- D-25: Settings stored in PostgreSQL — encrypted at rest if Fernet/AES via `cryptography` library is straightforward; plaintext minimum otherwise
- D-26: Settings include: TMDB API key, Radarr URL + API key + quality profile, Sonarr URL + API key, Plex token + URL, scheduled job timing, nightly sync limits
- D-27: `.env` remains supported as a fallback; DB-stored settings take precedence when present

#### Item 7 — Rotten Tomatoes Ratings (Research-First)
- D-28: Research third-party aggregator options (OMDb, MDBList, Streaming Availability API, similar)
- D-29: Researcher presents options with pros/cons before implementation decision
- D-30: Implementation NOT committed — user decides after research; if no clean solution exists, drop from Phase 6

#### Item 8 — Home Page Session Card Stats
- D-31: Replace deprecated "steps" stat with: watched count, total runtime, and started date
- D-32: Stats display inline on the session card

#### Item 9 — Now Playing Tile Additional Stats
- D-33: Add runtime, MPAA rating, and TMDB rating to the Now Playing tile
- D-34: Frontend display change only — fields already in session response data

### Claude's Discretion
- Exact visual design of the Movie Selection Splash (layout, spacing, poster size)
- Encryption library choice for Item 6 (Fernet is idiomatic for Python/FastAPI)
- Whether settings page lives at `/settings` route or as a modal/drawer
- TMDB link icon style (external link icon next to title vs clickable title text)

### Deferred Ideas (OUT OF SCOPE)
- Query Mode (QUERY-01 through QUERY-07)
- Eligible Actors grid TMDB links
- Sonarr integration beyond existing
- RT implementation (research only; actual implementation deferred pending findings)
</user_constraints>

---

## Summary

Phase 6 adds nine discrete features to CinemaChain. Most are frontend-heavy UI changes with minimal or no backend work. Items 1–3 and 6 require backend changes; Items 4, 5, 8, and 9 are frontend-only. Item 7 is a research task with no committed implementation.

The project is a mature FastAPI + SQLAlchemy async backend with a React/TypeScript + shadcn/ui frontend. All the key UI primitives (Dialog, DropdownMenu, Input, Checkbox) are already installed and used in the codebase. The primary architectural pattern is: React Query for server state, shadcn Dialog/DropdownMenu for modals and menus, and FastAPI endpoints with Pydantic schemas for backend changes.

The most complex items are Item 6 (settings DB table + new router + startup migration logic + optional encryption) and Item 2 (splash modal with new backend data needed: `overview` field not currently stored in the Movie model). Item 7 is a research deliverable only.

**Primary recommendation:** Tackle items in dependency order — Item 1 (fixes existing data) → Items 8/9 (frontend-only, lowest risk) → Items 3/4/5 (pure frontend additions) → Item 2 (needs backend `overview` field) → Item 6 (largest scope: new DB table + router + migration) → Item 7 (research presentation).

---

## Standard Stack

### Core (already installed — no new packages needed for most items)

| Library | Version | Purpose | Role in Phase 6 |
|---------|---------|---------|-----------------|
| React | 18.3.x | UI framework | All frontend items |
| @tanstack/react-query | 5.90.x | Server state | New queries for splash data, settings |
| @radix-ui/react-dialog | 1.1.x | Modal primitive | Item 2 splash, Item 3 modals |
| @radix-ui/react-dropdown-menu | 2.1.x | Menu primitive | Item 3 menu extensions |
| @radix-ui/react-checkbox | 1.3.x | Checkbox | Item 2 Radarr checkbox |
| lucide-react | 0.577.x | Icons | External link icon (Item 5) |
| FastAPI | 0.115.x | Backend framework | New settings router (Item 6) |
| SQLAlchemy async | 2.0.x | ORM | New AppSettings model (Item 6) |
| pydantic-settings | 2.6.x | .env parsing | .env migration on startup (Item 6) |
| alembic | 1.13.x | DB migrations | New app_settings table migration |

### New Dependencies Required

| Library | Version | Purpose | Item |
|---------|---------|---------|------|
| cryptography | >=42.0 | Fernet symmetric encryption for DB-stored secrets | Item 6 (if encryption chosen) |

**Installation (if encryption chosen for Item 6):**
```bash
# backend
pip install cryptography
# Add to requirements.txt: cryptography>=42.0
```

All other shadcn components (Input, Button, Card, Badge, Separator) are already present.

---

## Architecture Patterns

### Existing Code Entry Points

Every item maps to specific existing files:

| Item | Primary Files |
|------|--------------|
| 1 (Actor name fix) | `backend/app/routers/game.py` — `import_csv_session`, `_resolve_actor_tmdb_id`; `frontend/src/components/ChainHistory.tsx` |
| 2 (Movie splash) | `frontend/src/pages/GameSession.tsx` — `handleMovieConfirm`; `backend/app/routers/game.py` — `request_movie`; `backend/app/models/__init__.py` — Movie model |
| 3 (Menu consolidation) | `frontend/src/pages/GameSession.tsx` — DropdownMenuContent; `frontend/src/pages/GameLobby.tsx` — session card archive button |
| 4 (Chain search) | `frontend/src/components/ChainHistory.tsx` |
| 5 (TMDB links) | `frontend/src/components/ChainHistory.tsx`; eligible movies table in `GameSession.tsx`; new Movie Splash (Item 2) |
| 6 (Settings) | New: `backend/app/models/__init__.py` (AppSettings model), `backend/app/routers/settings.py`, `frontend/src/pages/Settings.tsx`; Modified: `backend/app/main.py`, `frontend/src/App.tsx`, `frontend/src/components/NavBar.tsx` |
| 7 (RT research) | Research deliverable only |
| 8 (Session card stats) | `frontend/src/pages/GameLobby.tsx` — session card rendering (line 246) |
| 9 (Now playing tile) | `frontend/src/pages/GameSession.tsx` — header section |

### Pattern 1: shadcn Dialog for Modals (Items 2, 3)

The codebase already uses `Dialog` + `DialogContent` + `DialogHeader` + `DialogFooter` for the "Delete Last Step" confirmation. Reuse verbatim.

```typescript
// Pattern from GameSession.tsx (lines 22-24) — already imported
import {
  Dialog, DialogContent, DialogHeader, DialogFooter,
  DialogTitle, DialogDescription,
} from "@/components/ui/dialog"

// State pattern: boolean open flag + data state
const [splashOpen, setSplashOpen] = useState(false)
const [splashMovie, setSplashMovie] = useState<EligibleMovieDTO | null>(null)
const [radarrChecked, setRadarrChecked] = useState(true)
```

### Pattern 2: DropdownMenu Extension (Item 3)

The session settings DropdownMenu is in `GameSession.tsx` at line 419–449. Extend by adding new `DropdownMenuItem` entries and a `DropdownMenuSeparator`.

```typescript
// Existing pattern — add after existing items:
<DropdownMenuSeparator />
<DropdownMenuItem onClick={() => setArchiveConfirmOpen(true)}>
  Archive Session
</DropdownMenuItem>
<DropdownMenuItem onClick={() => setEditNameOpen(true)}>
  Edit Session Name
</DropdownMenuItem>
```

### Pattern 3: Client-Side Filter (Item 4)

React state + `.filter()` on the existing `sorted` array in `ChainHistory.tsx`. No backend involvement — the full chain is already loaded in the session response.

```typescript
// In ChainHistory.tsx:
const [searchQuery, setSearchQuery] = useState("")
const visibleSteps = movieSteps.filter((step) => {
  if (!searchQuery) return true
  const q = searchQuery.toLowerCase()
  const actorStep = sorted.find(...)
  return (
    (step.movie_title ?? "").toLowerCase().includes(q) ||
    (actorStep?.actor_name ?? "").toLowerCase().includes(q)
  )
})
```

ChainHistory currently receives `steps: GameSessionStepDTO[]` as a prop. The search input and state should live inside `ChainHistory` itself to keep the parent clean.

### Pattern 4: TMDB External Links (Item 5)

TMDB URL pattern confirmed by CONTEXT.md:
- Movie: `https://www.themoviedb.org/movie/{tmdb_id}`
- Actor: `https://www.themoviedb.org/person/{tmdb_id}`

Use `ExternalLink` icon from lucide-react (or wrap title text as `<a>` with `target="_blank" rel="noopener noreferrer"`).

```typescript
// Eligible Movies table row — add link on title cell:
<a
  href={`https://www.themoviedb.org/movie/${movie.tmdb_id}`}
  target="_blank"
  rel="noopener noreferrer"
  className="inline-flex items-center gap-1 hover:underline"
  onClick={(e) => e.stopPropagation()}
>
  {movie.title}
  <ExternalLink className="w-3 h-3 text-muted-foreground" />
</a>
```

`onClick` stop-propagation is needed so the row's movie selection handler does not fire when clicking the link.

### Pattern 5: Settings DB Table + Router (Item 6)

New SQLAlchemy model pattern (follows existing `models/__init__.py` style):

```python
class AppSettings(Base):
    __tablename__ = "app_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    key: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    value: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
```

Key-value schema is the simplest approach and avoids schema migrations for every new setting. Use well-known keys: `tmdb_api_key`, `tmdb_base_url`, `radarr_url`, `radarr_api_key`, `radarr_quality_profile`, `sonarr_url`, `sonarr_api_key`, `plex_token`, `plex_url`, `tmdb_cache_time`, `tmdb_cache_top_n`.

**Migration:** Use Alembic. New file under `alembic/versions/`. The migration adds the `app_settings` table.

**Settings precedence logic** (in `settings.py` or startup lifespan):
1. On startup: query `app_settings` table for each key
2. If DB value present → use it
3. If DB value absent → fall back to pydantic-settings (reads `.env`)

**One-time .env migration** (in lifespan, runs once if DB is empty):
```python
# In lifespan, after DB verified:
from app.services.settings_migration import migrate_env_to_db_if_empty
await migrate_env_to_db_if_empty(db, settings)
```

**Fernet encryption** (if chosen):

```python
from cryptography.fernet import Fernet

# Derive key from a master secret (stored in .env as SETTINGS_ENCRYPTION_KEY)
# Usage:
fernet = Fernet(settings.settings_encryption_key.encode())
encrypted = fernet.encrypt(plaintext.encode()).decode()
decrypted = fernet.decrypt(encrypted.encode()).decode()
```

ENCRYPTION_KEY must be a 32-byte URL-safe base64-encoded key. Generate once: `Fernet.generate_key()`. Store this master key in `.env` — it never goes in DB. This is straightforward to implement (2-3 helper functions).

**Onboarding gate:** In `App.tsx`, wrap routes with a check — if settings query returns no TMDB key, render the onboarding screen fullscreen instead of routes.

```typescript
// App.tsx pattern:
const { data: settingsStatus } = useQuery({
  queryKey: ["settingsStatus"],
  queryFn: api.getSettingsStatus,
})

if (settingsStatus?.tmdb_configured === false) {
  return <OnboardingScreen />
}
```

### Pattern 6: Movie Overview Field (Item 2 dependency)

The `Movie` model does NOT currently store `overview`. The TMDB `/movie/{id}` endpoint returns it. Two approaches:

**Option A (recommended):** Add `overview` column to `Movie` model + Alembic migration. Populate it during the `_ensure_movie_cast_in_db` and `fetch_movie` flows. The splash then reads from DB.

**Option B:** Fetch `overview` live from TMDB at splash-open time (no DB storage). Simpler but adds TMDB latency to the splash interaction.

Given that `EligibleMovieResponse` already fetches rich movie data (runtime, mpaa, vote_average), Option A is cleaner. The splash endpoint can include `overview` in the eligible movie response or as a separate endpoint: `GET /game/sessions/{id}/movie/{tmdb_id}/details`.

**Decision guidance (discretion area):** Add `overview: str | None` to `Movie` model and backfill in `fetch_movie` and `_ensure_movie_cast_in_db`. Include it in `EligibleMovieResponse`. This avoids a separate splash endpoint.

### Pattern 7: Radarr Conditional (Item 2)

The current `handleMovieConfirm` always calls `api.requestMovie(...)`. For the splash:
- If `radarrChecked === true`: call `api.requestMovie(...)` as today
- If `radarrChecked === false`: call a variant that skips Radarr

Backend option: add `skip_radarr: bool = False` to `RequestMovieRequest` (additive, non-breaking). When `True`, the backend skips the Radarr call entirely.

This follows the same additive-field pattern used for `skip_actor: bool = False` (BUG-1 fix in Phase 5).

### Pattern 8: Edit Session Name (Item 3)

New backend endpoint needed:
```
PATCH /game/sessions/{session_id}/name
Body: { name: str }
Returns: GameSessionResponse
```

The endpoint checks name uniqueness (same logic as `create_session`), updates `session.name`, commits. Frontend mutation invalidates `["session", sid]` and `["activeSessions"]`.

### Anti-Patterns to Avoid

- **Don't add overview to StepResponse** — overview is only needed for the splash, not for chain history display.
- **Don't fetch overview from TMDB on every eligible-movies load** — fetch on movie detail load, cache in DB column.
- **Don't store the encryption master key in DB** — it must stay in `.env` / env variable. Only encrypted values go in DB.
- **Don't use `window.confirm()` for the Movie Splash** — existing code uses it (line 212 in GameSession.tsx) but D-04 explicitly replaces this with the new Dialog.
- **Don't make ChainHistory search stateful in the parent** — keep search state inside `ChainHistory` component to avoid prop drilling and parent re-renders.
- **Don't add TMDB links to Eligible Actors grid** — explicitly out of scope (D-20).

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Symmetric encryption of secrets | Custom XOR or base64 "obfuscation" | `cryptography.fernet.Fernet` | Battle-tested AES-128-CBC with HMAC authentication |
| Modal dialogs | Custom overlay/portal components | `shadcn Dialog` (already installed) | Radix UI handles focus trap, keyboard dismiss, accessibility |
| Dropdown menus | Custom click-away menus | `shadcn DropdownMenu` (already installed) | Radix UI handles positioning, keyboard nav |
| External link icons | SVG inline or custom component | `lucide-react ExternalLink` (already installed) | Consistent icon system already in use |
| DB key-value pattern | JSON blob column or multiple columns | key/value string pairs in `app_settings` table | Simple, schema-stable, easy to query |
| Settings onboarding blocking | Custom routing guard | Conditional render in App.tsx root | React Query check at root level is the React pattern |

---

## Item 7: Rotten Tomatoes Research Findings

This section fulfills D-28/D-29. No implementation is committed (D-30).

### Options Comparison

| Option | Source | Free Tier | Rate Limit | RT Score Freshness | TMDB ID Lookup | Reliability |
|--------|--------|-----------|-----------|-------------------|----------------|-------------|
| OMDb API | IMDB-sourced; RT scores scraped | 1,000 req/day | 1,000/day free; paid plans available | Days to weeks stale; RT scores not always present | By IMDB ID (need separate TMDB→IMDB mapping) | MEDIUM — RT data is "Ratings" array, not always populated |
| MDBList API | Aggregates IMDB, TMDB, RT, Metacritic | 1,000 req/day | 1,000/day free | Days to weeks stale per docs | By TMDB ID directly | MEDIUM — explicitly documented as periodically refreshed, not live |
| TMDB API | TMDB native | Unlimited (rate-limited) | ~40 req/10s | N/A — TMDB does not have RT scores | Native | HIGH for TMDB data; no RT |
| Official RT API | Rotten Tomatoes | No public API | N/A — not available | N/A | N/A | No public tier |
| RapidAPI RT scrapers | Third-party scrapers | Paid only or tiny free tier | Varies | Hours-to-days | Varies | LOW — fragile, ToS risk |

### Recommendation for User Decision

**Best fit for CinemaChain: MDBList API**
- Free tier: 1,000 requests/day — sufficient for on-demand lookups (not batched sync)
- Accepts TMDB ID directly (no IMDB ID mapping needed)
- Returns RT Tomatometer + Audience Score in addition to IMDB/Metacritic
- Caveats: scores can be days-to-weeks stale; free tier is 1,000/day (may be tight if used for every page load; solve by caching score in DB alongside TMDB data)

**OMDb is second choice.** It requires TMDB→IMDB ID mapping (add `imdb_id` column to Movie, populate from TMDB `/movie/{id}` response which returns `imdb_id`). The RT score in OMDb's `Ratings` array is not guaranteed to be present.

**Recommend: MDBList if implementing.** Cache RT score in a new `rt_score` column on the `Movie` model; fetch on demand when displaying the splash; background-refresh if older than 7 days. If MDBList free tier proves insufficient, upgrade to a paid plan ($2–5/month per docs).

**If dropped from Phase 6:** No changes needed. The existing architecture is unaffected.

---

## Common Pitfalls

### Pitfall 1: `overview` field not in Movie model
**What goes wrong:** Item 2 (Movie Splash) requires the TMDB `overview` (plot summary). The current `Movie` model and all existing fetch paths do not store or return this field.
**Why it happens:** The model was built for the game mechanic, not for detailed movie display.
**How to avoid:** Add `overview: str | None` column to `Movie` model via Alembic migration. Update `fetch_movie`, `_ensure_movie_cast_in_db`, and the `_backfill_movie_posters_background` task to store it when available. Add `overview` to `EligibleMovieResponse`.
**Warning signs:** Splash renders but plot summary is always empty or "N/A".

### Pitfall 2: Fernet key not persisted across container restarts
**What goes wrong:** If the Fernet master key (SETTINGS_ENCRYPTION_KEY) is generated at runtime instead of stored in `.env`, all DB-encrypted secrets become unreadable after restart.
**Why it happens:** Developer generates key in startup code instead of a one-time setup step.
**How to avoid:** The Fernet key must be user-provided in `.env` at setup time. Document key generation (`Fernet.generate_key().decode()`) in the Settings onboarding screen. The key is NOT stored in DB.
**Warning signs:** Settings page shows errors or blank values after container restart.

### Pitfall 3: Archive button removal breaks GameLobby layout
**What goes wrong:** Removing the Archive button from the session card (D-11) may break the flex layout of the card's action area if other buttons depend on its presence for spacing.
**Why it happens:** The current card has `flex flex-wrap items-center gap-2` with Archive + Continue buttons together.
**How to avoid:** After removing Archive button, verify the card still looks correct with only the Continue button. Adjust padding/alignment if needed.
**Warning signs:** Session card "Continue →" button appears misaligned or too wide.

### Pitfall 4: Session name edit — uniqueness check race condition
**What goes wrong:** User renames session to same name as another existing session.
**Why it happens:** The `PATCH /sessions/{id}/name` endpoint must exclude the session being renamed from the uniqueness check.
**How to avoid:** Uniqueness query: `WHERE name = :name AND id != :session_id AND status NOT IN ('archived', 'ended')`.
**Warning signs:** User cannot rename a session back to its original name (incorrectly blocked by self-match).

### Pitfall 5: CSV actor name not resolved if Actor row already exists in DB
**What goes wrong:** Item 1 — actor TMDB ID exists in the step but actor name is NULL or wrong. The fix must resolve the name from TMDB even if the Actor row exists (check `actor.name` not just existence).
**Why it happens:** CSV import path stores `actor_tmdb_id` from the override but may not have populated `actor_name` in the step if TMDB fetch was skipped.
**How to avoid:** In the import path, after resolving `actor_id`, always check: if `actor_name is None` → call `tmdb.fetch_person(actor_id)` to get canonical name. Store result in step.
**Warning signs:** Chain history shows blank or "Actor {tmdb_id}" placeholder for CSV-imported actors.

### Pitfall 6: Onboarding screen flashes on every page load before settings load
**What goes wrong:** Settings query is async; during the loading state, the onboarding screen briefly renders before the real app appears.
**Why it happens:** The gate renders `<OnboardingScreen />` when `settingsStatus?.tmdb_configured === false`, but during load `settingsStatus` is `undefined`.
**How to avoid:** Gate on `settingsStatus !== undefined && settingsStatus.tmdb_configured === false`. During loading, render a minimal spinner or nothing.
**Warning signs:** App flashes onboarding screen for ~200ms on every load.

### Pitfall 7: TMDB external link click fires movie selection
**What goes wrong:** Clicking the TMDB link in the Eligible Movies table also triggers `handleMovieConfirm` or the row's onClick.
**Why it happens:** The link is nested inside a clickable row/cell without event propagation stop.
**How to avoid:** Add `e.stopPropagation()` on the anchor's `onClick`. Confirm the row's clickable area does not use a `<tr onClick>` wrapper that the link is inside.
**Warning signs:** Movie splash opens when user clicks the TMDB link icon.

---

## Code Examples

### Example 1: Movie Splash — replace window.confirm in handleMovieConfirm

```typescript
// GameSession.tsx — replace window.confirm block (line 212-215):
// BEFORE:
const confirmed = window.confirm(`Select "${movie.title}" as your next movie?`)
if (!confirmed) return

// AFTER: open splash instead
setSplashMovie(movie)
setRadarrChecked(true)
setSplashOpen(true)
// Actual confirm/advance logic moves to handleSplashConfirm(movie, radarrChecked)
```

### Example 2: Radarr skip_radarr field (backend)

```python
# In RequestMovieRequest — add field:
class RequestMovieRequest(BaseModel):
    movie_tmdb_id: int
    movie_title: str | None = None
    skip_actor: bool = False
    skip_radarr: bool = False  # NEW — Item 2: user unchecked Radarr checkbox in splash

# In request_movie endpoint, guard the Radarr call:
if not body.skip_radarr:
    try:
        radarr_status = await radarr.add_movie(...)
    except Exception:
        radarr_status = "error"
else:
    radarr_status = "skipped"
```

### Example 3: AppSettings model

```python
# backend/app/models/__init__.py — add after WatchEvent:
class AppSettings(Base):
    __tablename__ = "app_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    key: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    value: Mapped[Optional[str]] = mapped_column(sa.Text, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
```

### Example 4: Settings precedence in lifespan

```python
# backend/app/main.py — in lifespan, after DB verify:
from sqlalchemy import select
from app.models import AppSettings

async def get_db_setting(db_session, key: str) -> str | None:
    row = await db_session.execute(select(AppSettings).where(AppSettings.key == key))
    s = row.scalar_one_or_none()
    return s.value if s else None

# Use: db_api_key = await get_db_setting(db, "tmdb_api_key") or settings.tmdb_api_key
```

### Example 5: ChainHistory search (pure frontend)

```typescript
// ChainHistory.tsx — add at top of component body:
const [searchQuery, setSearchQuery] = useState("")

// Replace: const movieSteps = sorted.filter(...)
// With filtered version:
const allMovieSteps = sorted.filter((s) => s.actor_tmdb_id === null)
const movieSteps = searchQuery
  ? allMovieSteps.filter((step) => {
      const q = searchQuery.toLowerCase()
      const actorStep = sorted.find(
        (s) => s.step_order === step.step_order + 1 && s.actor_tmdb_id !== null
      )
      return (
        (step.movie_title ?? "").toLowerCase().includes(q) ||
        (actorStep?.actor_name ?? "").toLowerCase().includes(q)
      )
    })
  : allMovieSteps

// Add above table:
<Input
  placeholder="Search chain..."
  value={searchQuery}
  onChange={(e) => setSearchQuery(e.target.value)}
  className="mb-3"
/>
```

### Example 6: Session card stats update (Item 8)

The `GameSessionDTO` already returns `watched_count`, `watched_runtime_minutes`, and `created_at` from `GameSessionResponse`. The current card at GameLobby.tsx line 246 reads:
```
{session.watched_count} watched · {session.step_count ?? 0} steps · started {formatSessionAge(session.created_at ?? "")}
```
This is already partially updated. Replace `{session.step_count ?? 0} steps` with runtime display:
```typescript
const runtimeHours = Math.floor((session.watched_runtime_minutes ?? 0) / 60)
const runtimeMins = (session.watched_runtime_minutes ?? 0) % 60
const runtimeStr = runtimeHours > 0 ? `${runtimeHours}h ${runtimeMins}m` : `${runtimeMins}m`
// Display: "{watched_count} watched · {runtimeStr} · started {age}"
```

---

## State of the Art

| Old Approach | Current Approach | Impact |
|--------------|------------------|--------|
| `window.confirm()` for movie selection | shadcn Dialog splash (Item 2) | Richer UX, supports poster + metadata display |
| Archive button on home page card | Archive in session dropdown menu (Item 3) | Cleaner card layout, consistent action placement |
| Steps count in session card stat | Watched count + runtime + started date (Item 8) | More meaningful session summary |

**`overview` field:** Not currently stored on Movie model. Needs new column + migration.

**`edit session name` endpoint:** Does not exist yet. PATCH endpoint is new work.

---

## Open Questions

1. **Overview field — store in Movie model or fetch live?**
   - What we know: TMDB `/movie/{id}` returns `overview`; current Movie model does not store it
   - What's unclear: User did not specify whether to add DB column or fetch live at splash time
   - Recommendation: Add `overview: Text | None` to Movie model (Option A) — avoids TMDB latency at splash open, consistent with existing caching strategy

2. **Settings page route vs modal/drawer**
   - What we know: D-21 says "accessible via NavBar or settings icon"; marked as Claude's discretion
   - What's unclear: Whether to add `/settings` route (needs NavBar link + route in App.tsx) or render as a modal triggered from NavBar
   - Recommendation: `/settings` route — simpler to test, bookmarkable, consistent with existing `/archived` route pattern

3. **Fernet master key on fresh install**
   - What we know: Encryption key must be user-provided; onboarding screen is blocking
   - What's unclear: Should the onboarding screen generate and display the key for the user to copy to `.env`?
   - Recommendation: Generate a random key on first-run and store it in the DB under a non-encrypted key (`settings_encryption_key`) as a bootstrap. Simpler than requiring manual key setup. Risk: key in DB (not .env), but acceptable for a home-server single-user app.

4. **RT scores — MDBList free tier 1,000 req/day sufficient?**
   - What we know: 1,000 req/day free; scores cached in DB after first fetch; refresh weekly
   - What's unclear: Exact MDBList response schema not confirmed (Apiary docs require JS rendering)
   - Recommendation: User should confirm MDBList tier suitability before committing to implementation. On-demand fetch + 7-day DB cache keeps daily request count low (likely < 50/day for typical usage).

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 8.3.4 (backend) + vitest 4.1.0 (frontend) |
| Config file | `backend/pytest.ini` or inline; `frontend/vite.config.ts` with vitest config |
| Quick run command (backend) | `cd /Users/Oreo/Projects/backend && pytest tests/test_game.py -x -q` |
| Quick run command (frontend) | `cd /Users/Oreo/Projects/frontend && npm test` |
| Full suite (backend) | `cd /Users/Oreo/Projects/backend && pytest -x -q` |
| Full suite (frontend) | `cd /Users/Oreo/Projects/frontend && npm test` |

### Phase Requirements to Test Map

| Item | Behavior | Test Type | Automated Command | File Exists? |
|------|----------|-----------|-------------------|-------------|
| Item 1 (actor name) | CSV import resolves actor name when TMDB ID override present | unit (backend) | `pytest tests/test_game.py::test_csv_actor_name_resolved -x` | ❌ Wave 0 |
| Item 2 (splash data) | EligibleMovieResponse includes overview field | unit (backend) | `pytest tests/test_game.py::test_eligible_movie_overview_field -x` | ❌ Wave 0 |
| Item 2 (skip_radarr) | request_movie with skip_radarr=True skips Radarr call | unit (backend) | `pytest tests/test_game.py::test_request_movie_skip_radarr -x` | ❌ Wave 0 |
| Item 3 (rename endpoint) | PATCH /sessions/{id}/name updates name; blocks duplicate | unit (backend) | `pytest tests/test_game.py::test_rename_session -x` | ❌ Wave 0 |
| Item 4 (chain search) | ChainHistory filters rows matching search input | unit (frontend) | `npm test -- ChainHistory` | ❌ Wave 0 |
| Item 6 (settings CRUD) | GET/PUT /settings returns and stores settings | unit (backend) | `pytest tests/test_settings.py -x` | ✅ (file exists, extend) |
| Item 6 (precedence) | DB setting overrides .env on startup | unit (backend) | `pytest tests/test_settings.py::test_db_overrides_env -x` | ❌ Wave 0 |
| Item 8 (session card) | GameLobby displays watched_runtime_minutes on card | unit (frontend) | `npm test -- GameLobby` | ❌ Wave 0 |

### Sampling Rate

- **Per task commit:** `pytest tests/test_game.py -x -q` (backend tasks) or `npm test` (frontend tasks)
- **Per wave merge:** Full suite: `pytest -x -q && npm test`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `backend/tests/test_game.py` — add stubs: `test_csv_actor_name_resolved`, `test_eligible_movie_overview_field`, `test_request_movie_skip_radarr`, `test_rename_session`
- [ ] `backend/tests/test_settings.py` — add stub: `test_db_overrides_env` (file exists, append)
- [ ] `frontend/src/components/__tests__/ChainHistory.test.tsx` — new file, covers Item 4 search behavior
- [ ] `frontend/src/pages/__tests__/GameLobby.test.tsx` — new file, covers Item 8 stats display
- [ ] Alembic migration file for `app_settings` table and `overview` column on `movies`

*(All backend stubs should use the asyncpg-skip pattern: `try: import asyncpg except ImportError: pytest.skip(...)` consistent with existing test conventions.)*

---

## Sources

### Primary (HIGH confidence)
- Direct read of `backend/app/routers/game.py` — existing endpoint signatures, request/response models, Radarr integration, _resolve_actor_tmdb_id
- Direct read of `backend/app/models/__init__.py` — Movie, Actor, GameSession, GameSessionStep schema
- Direct read of `backend/app/settings.py` — pydantic-settings configuration, all current env keys
- Direct read of `frontend/src/pages/GameSession.tsx` — DropdownMenu structure, handleMovieConfirm, shadcn imports
- Direct read of `frontend/src/pages/GameLobby.tsx` — session card structure, archive button location, stats display (line 246)
- Direct read of `frontend/src/components/ChainHistory.tsx` — table structure, actor/movie step pairing logic
- Direct read of `frontend/src/App.tsx` — route structure
- Direct read of `frontend/src/components/NavBar.tsx` — existing nav links
- Direct read of `frontend/package.json` — installed libraries (shadcn, lucide-react, vitest)
- Direct read of `backend/requirements.txt` — installed packages, no cryptography present

### Secondary (MEDIUM confidence)
- CONTEXT.md canonical refs section — confirmed file paths and reusable patterns
- WebFetch `docs.mdblist.com` — 1,000 req/day free tier confirmed; full API schema not resolved (JS-rendered)
- WebSearch OMDb API — RT scores in Ratings array, free tier 1,000/day, IMDB ID dependency confirmed

### Tertiary (LOW confidence)
- MDBList full response schema (RT score field names, TMDB ID query format) — not confirmed; Apiary docs require JS rendering. Verify before implementation.
- OMDb RT score reliability/freshness for specific movies — anecdotal; varies by movie popularity.

---

## Metadata

**Confidence breakdown:**
- Items 1–5, 8–9 (frontend/light backend): HIGH — all relevant code read directly
- Item 6 (settings): HIGH for architecture; MEDIUM for encryption (Fernet straightforward but `cryptography` not yet in requirements)
- Item 7 (RT research): MEDIUM — free tier limits confirmed; API response schemas not fully confirmed

**Research date:** 2026-03-22
**Valid until:** 2026-04-22 (stable stack; MDBList/OMDb API terms may change)
