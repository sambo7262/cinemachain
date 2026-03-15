# Phase 3: Movie Game - Research

**Researched:** 2026-03-15
**Domain:** React SPA (Vite + Tailwind + shadcn/ui), FastAPI game session API, Radarr HTTP integration, PostgreSQL session schema
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Game startup: watched movie selection, title search (any movie, not just Plex-watched), or CSV import (Movie Name, Actor Name, Order columns)
- One session at a time — only one active or paused session exists at any given moment
- Sessions can be explicitly paused; incoming Plex watch events do NOT affect a paused session
- Session ends on manual termination OR chain exhaustion
- Frontend stack: React + Vite + Tailwind CSS + shadcn/ui
- Two-tab game panel: "Eligible Actors" tab | "Eligible Movies" tab
- Eligible Actors panel: cast of current movie, excluding already-picked actors
- Selecting an actor switches to Eligible Movies tab (that actor's unwatched filmography)
- Eligible Movies without a selected actor shows ALL eligible movies across all currently-eligible actors (combined view)
- Movie cards show: poster, title, TMDB vote_average, genre(s), runtime, "via [Actor Name]" in combined view
- Sort and filter by rating, genre, and runtime
- Toggle: unwatched-only vs all movies with watched badges; only unwatched movies are selectable
- Chain history: visible in-UI sequence Movie → Actor → Movie → Actor — table is acceptable baseline
- Session advances ONLY after chosen movie is marked as watched (Plex webhook or manual mark)
- UI prompt on watch: "[Movie] marked as watched — [Continue the chain]"
- Radarr request triggered ONLY if movie does not already exist in Radarr
- No Radarr call at session start — only when user picks a movie to request
- Dark theme by default, responsive for TV and tablet (large tap targets, readable at distance)
- Replace `frontend/index.html` placeholder with full React + Vite project

### Claude's Discretion
- TMDB name-to-ID disambiguation when CSV lookup returns multiple matches (pick highest vote_count)
- Chain history visual treatment (make it feel like a story, not a plain list)
- Game session and step ORM schema design
- RadarrClient service implementation (mirrors TMDBClient pattern)
- Frontend routing (likely React Router or TanStack Router SPA)
- Exact shadcn/ui component choices for tabs, cards, filters, and chain history

### Deferred Ideas (OUT OF SCOPE)
- "Most connectable" actor sort — GAME-EX-01, v2
- Genre-constrained game mode — GAME-EX-03, v2
- Cross-session chain history / saved chains — GAME-EX-02, v2
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| GAME-01 | User can start a Movie Game session by selecting any movie as starting point | TMDB search endpoint for title lookup; watched-movie list from WatchEvent table; session creation API |
| GAME-02 | Eligible Actors panel: cast of current movie, excluding already-picked actors | Credits join with exclusion of picked_actor_tmdb_ids; existing GET /movies/{id} + credits |
| GAME-03 | User selects an actor to view Eligible Movies panel (unwatched filmography) | Existing GET /actors/{id}/filmography with watch state; GameSession stores current_actor_tmdb_id |
| GAME-04 | Session tracks picked actors — no actor can repeat within a session | GameSessionStep records actor picks; eligible query filters on picked set |
| GAME-05 | User can sort Eligible Movies by genre, TMDB rating, or aggregated rating | Client-side sort (all data already returned); vote_average on Movie model |
| GAME-06 | Toggle between unwatched-only or all movies with watched badges | Client-side filter; watched flag already in filmography response |
| GAME-07 | Only unwatched movies are selectable in Game mode | API + UI enforce: selectable=False when watched=True |
| GAME-08 | User requests a movie, triggering automatic Radarr queue request | RadarrClient.add_movie; check-exists-first via GET /api/v3/movie?tmdbId=X |
</phase_requirements>

---

## Summary

Phase 3 is the largest phase in the project — it adds a full React SPA (replacing the static nginx placeholder), a game session API with PostgreSQL persistence, and a Radarr integration service. The backend work is a natural extension of the Phase 2 patterns: a new `app/routers/game.py`, two new ORM models (`GameSession` + `GameSessionStep`), a new Alembic migration, and a `RadarrClient` modelled on `TMDBClient`. The frontend is a greenfield Vite + React + TypeScript + Tailwind + shadcn/ui project built in the `frontend/` directory and served by the existing nginx container.

The Radarr integration should be implemented as a direct `httpx.AsyncClient` wrapper (matching `TMDBClient` exactly) rather than using `pyarr`, which is synchronous and unmaintained since July 2023. The two key Radarr API calls are: `GET /api/v3/movie?tmdbId={id}` (check exists) and `POST /api/v3/movie` (add with lookup payload). The Radarr `radarr_url` and `radarr_api_key` settings already exist in `app/settings.py`.

The frontend routing decision is React Router v6 (via `react-router-dom`) for SPA mode — it is simpler for a two-screen app than TanStack Router, and the project has no need for the advanced type-safe search-param management TanStack Router provides. The UI is structured as two primary views: Game (tabs: Eligible Actors / Eligible Movies) and a session-start/lobby screen.

**Primary recommendation:** Build `RadarrClient` as a thin `httpx.AsyncClient` wrapper; build the frontend as `frontend/` Vite project with multi-stage Docker build replacing the current nginx placeholder; keep all game state in PostgreSQL from the first line of code — NAS containers restart unexpectedly.

---

## Standard Stack

### Core Backend
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| FastAPI | 0.115.6 | Game session API router | Already in project |
| SQLAlchemy asyncio | 2.0.36 | GameSession/Step ORM models | Already in project |
| asyncpg | 0.29.0 | Async PostgreSQL driver | Already in project |
| httpx | 0.27.2 | RadarrClient HTTP calls | Already in project; matches TMDBClient pattern |
| Alembic | 1.13.3 | Migration for game tables | Already in project |

### Core Frontend
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| React | 18.x | SPA component model | shadcn/ui targets React 18 |
| Vite | 5.x | Build tool + dev server | Fast, standard for React SPA |
| TypeScript | 5.x | Type safety | shadcn/ui ships TypeScript |
| Tailwind CSS | 3.x | Utility CSS | shadcn/ui v0 components use Tailwind 3 |
| shadcn/ui | latest | UI component library | Locked decision |
| react-router-dom | 6.x | SPA routing | Lightweight, widely documented, simpler than TanStack for this app |
| @tanstack/react-query | 5.x | Server state / cache | De-facto standard for FastAPI + React data fetching |

**Important:** Use Tailwind CSS v3, NOT v4. shadcn/ui's component set is authored for Tailwind v3. Mixing shadcn/ui with Tailwind v4 causes style breakage (v4 removed the `tailwind.config.js` system that shadcn/ui's theming depends on).

### Supporting Frontend
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| lucide-react | latest | Icon set | shadcn/ui uses lucide-react by default |
| clsx + tailwind-merge | latest | Conditional class merging | Required by shadcn/ui `cn()` utility |
| axios | — | **Do not use** | Prefer native fetch or @tanstack/react-query; axios adds weight |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| react-router-dom | TanStack Router | TanStack Router wins on type safety but is heavier and overkill for 2 screens |
| @tanstack/react-query | SWR | react-query has wider adoption and better mutation support; SWR fine but no advantage here |
| httpx RadarrClient | pyarr | pyarr is synchronous (blocks event loop in async FastAPI); last release July 2023 |
| Tailwind v3 | Tailwind v4 | shadcn/ui components are authored for v3; v4 changes config system |

### Installation

**Frontend (run from `frontend/` after Vite scaffold):**
```bash
npm create vite@latest . -- --template react-ts
npm install -D tailwindcss@3 postcss autoprefixer
npx tailwindcss init -p
npx shadcn@latest init
npm install react-router-dom @tanstack/react-query lucide-react
```

**Backend additions to `requirements.txt`:**
```
# No new packages needed — httpx, fastapi, sqlalchemy already present
# csv module is Python stdlib — no install needed
```

---

## Architecture Patterns

### Backend: New Files

```
backend/app/
├── routers/game.py               # All game session endpoints
├── services/radarr.py            # RadarrClient (mirrors tmdb.py)
└── models/__init__.py            # Add GameSession + GameSessionStep

backend/alembic/versions/
└── 20260315_0002_game_session_schema.py   # New migration
```

### Frontend: New Project Structure

```
frontend/
├── Dockerfile                    # Multi-stage: node build → nginx serve
├── index.html                    # Vite entry (replaces static placeholder)
├── vite.config.ts
├── tailwind.config.js
├── tsconfig.json
├── src/
│   ├── main.tsx                  # React root + QueryClient + Router
│   ├── App.tsx                   # Route definitions
│   ├── lib/
│   │   ├── api.ts                # Typed fetch wrappers (base URL = /api)
│   │   └── utils.ts              # shadcn cn() utility
│   ├── components/
│   │   ├── ui/                   # shadcn/ui generated components
│   │   ├── MovieCard.tsx
│   │   ├── ActorCard.tsx
│   │   └── ChainHistory.tsx
│   └── pages/
│       ├── GameLobby.tsx         # Session start — movie search / watched list / CSV import
│       └── GameSession.tsx       # Two-tab game panel (Eligible Actors | Eligible Movies)
```

### Pattern 1: RadarrClient (mirrors TMDBClient)

**What:** Async httpx wrapper stored on `app.state`; all Radarr calls go through it.
**When to use:** Any endpoint needing to add or check movies in Radarr.

```python
# Source: mirrors app/services/tmdb.py pattern established in Phase 2
class RadarrClient:
    def __init__(self, base_url: str, api_key: str) -> None:
        self._client = httpx.AsyncClient(
            base_url=base_url,
            headers={"X-Api-Key": api_key},
            timeout=15.0,
        )

    async def movie_exists(self, tmdb_id: int) -> bool:
        """Check if movie is already in Radarr via GET /api/v3/movie?tmdbId=X."""
        r = await self._client.get("/api/v3/movie", params={"tmdbId": tmdb_id})
        r.raise_for_status()
        return len(r.json()) > 0

    async def add_movie(self, lookup_payload: dict) -> dict:
        """POST /api/v3/movie with lookup payload from /api/v3/movie/lookup."""
        r = await self._client.post("/api/v3/movie", json=lookup_payload)
        if r.status_code == 400:
            # Radarr returns 400 when movie already exists — treat as success
            return {"status": "already_exists"}
        r.raise_for_status()
        return r.json()

    async def lookup_movie(self, tmdb_id: int) -> dict | None:
        """GET /api/v3/movie/lookup?term=tmdb:{id} — returns Radarr's full movie object."""
        r = await self._client.get(
            "/api/v3/movie/lookup",
            params={"term": f"tmdb:{tmdb_id}"},
        )
        r.raise_for_status()
        results = r.json()
        return results[0] if results else None

    async def close(self) -> None:
        await self._client.aclose()
```

### Pattern 2: GameSession + GameSessionStep ORM Schema

**What:** Two tables — one row per session, one row per game step (actor pick or movie pick).
**When to use:** All game state reads and writes.

```python
# Source: SQLAlchemy 2.0 mapped_column pattern from existing models/__init__.py
import enum

class SessionStatus(str, enum.Enum):
    active = "active"
    paused = "paused"
    ended = "ended"

class GameSession(Base):
    __tablename__ = "game_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    current_movie_tmdb_id: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    steps: Mapped[list["GameSessionStep"]] = relationship(
        back_populates="session", lazy="raise", order_by="GameSessionStep.step_order"
    )

class GameSessionStep(Base):
    __tablename__ = "game_session_steps"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("game_sessions.id"), nullable=False, index=True)
    step_order: Mapped[int] = mapped_column(Integer, nullable=False)
    movie_tmdb_id: Mapped[int] = mapped_column(Integer, nullable=False)
    actor_tmdb_id: Mapped[int | None] = mapped_column(Integer, nullable=True)  # null on final movie step
    actor_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    movie_title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    session: Mapped["GameSession"] = relationship(back_populates="steps", lazy="raise")
```

**Constraint:** Only one active session at a time is enforced at the API layer (not DB constraint) — check before creating.

### Pattern 3: Eligible Actors Query

**What:** Join credits → actors for current movie, excluding actors whose `tmdb_id` is in the session's picked set.
**When to use:** GET `/game/sessions/{id}/eligible-actors`

```python
# Source: SQLAlchemy 2.0 async select pattern from existing routers/actors.py
picked_ids = [step.actor_tmdb_id for step in session.steps if step.actor_tmdb_id]

stmt = (
    select(Actor, Credit)
    .join(Credit, Credit.actor_id == Actor.id)
    .join(Movie, Movie.id == Credit.movie_id)
    .where(Movie.tmdb_id == session.current_movie_tmdb_id)
    .where(Actor.tmdb_id.not_in(picked_ids) if picked_ids else True)
    .options(selectinload(Credit.movie))
)
```

### Pattern 4: Radarr Add Flow

**What:** Two-step: lookup then add. Never add without a lookup first.
**When to use:** POST `/game/sessions/{id}/request-movie`

```python
# Correct Radarr add flow
async def request_movie(tmdb_id: int, radarr: RadarrClient) -> dict:
    # Step 1: check if already in Radarr
    if await radarr.movie_exists(tmdb_id):
        return {"status": "already_in_radarr"}
    # Step 2: lookup to get full Radarr movie object (title, year, images, etc.)
    movie_payload = await radarr.lookup_movie(tmdb_id)
    if not movie_payload:
        raise HTTPException(502, "Movie not found in Radarr lookup")
    # Step 3: add with search
    movie_payload["monitored"] = True
    movie_payload["addOptions"] = {"searchForMovie": True}
    # rootFolderPath and qualityProfileId come from settings or Radarr defaults
    return await radarr.add_movie(movie_payload)
```

**Key:** The lookup payload already contains `title`, `titleSlug`, `images`, `year`, `tmdbId` — Radarr requires these in the POST body. Build the payload from the lookup result, not from scratch.

### Pattern 5: React Two-Tab Game Panel

**What:** shadcn/ui `Tabs` wrapping two controlled panels.
**When to use:** Main game view.

```typescript
// Source: ui.shadcn.com/docs/components/radix/tabs
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"

<Tabs value={activeTab} onValueChange={setActiveTab}>
  <TabsList className="grid w-full grid-cols-2">
    <TabsTrigger value="actors">Eligible Actors</TabsTrigger>
    <TabsTrigger value="movies">Eligible Movies</TabsTrigger>
  </TabsList>
  <TabsContent value="actors">
    <ActorsPanel sessionId={sessionId} onActorSelect={handleActorSelect} />
  </TabsContent>
  <TabsContent value="movies">
    <MoviesPanel sessionId={sessionId} selectedActorId={selectedActor} />
  </TabsContent>
</Tabs>
```

### Pattern 6: CSV Import

**What:** Parse CSV in frontend (browser FileReader), send parsed rows to backend. Backend resolves TMDB IDs via `/search/movie` then creates session.
**When to use:** Session start via CSV import.

```typescript
// Frontend parses CSV columns: Movie Name, Actor Name, Order
// Sends array of {movieName, actorName, order} to POST /game/sessions/import-csv
```

```python
# Backend: TMDB search for each movie name
async def resolve_tmdb_id(title: str, tmdb: TMDBClient) -> int | None:
    r = await tmdb._client.get("/search/movie", params={"query": title})
    results = r.json().get("results", [])
    if not results:
        return None
    # Claude's discretion: pick highest vote_count when multiple matches
    return max(results, key=lambda m: m.get("vote_count", 0))["id"]
```

### Frontend Docker: Multi-Stage Build

```dockerfile
# Stage 1: build
FROM node:20-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

# Stage 2: serve
FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
```

**nginx.conf must include `try_files $uri $uri/ /index.html;`** for React Router client-side routing. Without this, refreshing any non-root URL returns 404.

### Anti-Patterns to Avoid

- **Using pyarr in FastAPI**: pyarr is synchronous (`requests`-based); calling it from an async endpoint blocks the event loop. Use `httpx.AsyncClient` directly.
- **Storing game state in memory**: NAS containers restart unexpectedly. All session state must be in PostgreSQL before returning 200.
- **Skipping the Radarr lookup step**: `POST /api/v3/movie` requires `title`, `titleSlug`, `images`, `year` — these fields come from the lookup endpoint. The TMDB data in your DB does not include `titleSlug` or `images`.
- **Using Tailwind v4 with shadcn/ui**: shadcn/ui v0 components use the `tailwind.config.js` theme extension system; Tailwind v4 replaces this with CSS-based config and breaks shadcn/ui's CSS variable setup.
- **Using `lazy="select"` or default lazy loading**: All ORM models use `lazy="raise"`. Game queries must use `selectinload()` explicitly.
- **Building eligible-actors filtering in Python after a full fetch**: Push the exclusion into SQL to avoid loading all actor rows then filtering in Python.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| UI component tabs | Custom tab toggle | shadcn/ui `Tabs` (Radix UI) | Keyboard nav, ARIA, focus management built in |
| Data fetching + cache invalidation | useEffect + useState fetch | @tanstack/react-query | Handles loading/error states, stale-while-revalidate, mutation invalidation |
| Client-side routing | Manual history.pushState | react-router-dom | Handles browser history, nested routes, `<Link>` prefetching |
| Movie poster images | Manual TMDB image URL construction | Use constant: `https://image.tmdb.org/t/p/w500{poster_path}` | Standard TMDB image base URL; width tokens: w92, w185, w342, w500, w780, original |
| CSV parsing | String.split() | Browser `FileReader` + manual CSV parse or `papaparse` | Quote handling, encoding, edge cases |
| Radarr movie payload construction | Manually building all fields | Lookup first (`/api/v3/movie/lookup?term=tmdb:{id}`), then add the returned object | Radarr lookup returns all required fields (`titleSlug`, `images`, `qualityProfileId` etc.) |

**Key insight:** The Radarr lookup-then-add flow is the correct pattern documented by the Radarr project. Constructing the POST body manually from TMDB data will fail because Radarr requires internal fields (`titleSlug`, `images`) that TMDB does not provide.

---

## Common Pitfalls

### Pitfall 1: Radarr Returns 400 on Duplicate — Not an Error
**What goes wrong:** `RadarrClient.add_movie` raises `httpx.HTTPStatusError` on 400, crashing the request even though the movie already exists.
**Why it happens:** Radarr returns HTTP 400 with body `{"message":"MovieExistsValidator"}` when a duplicate add is attempted. This is documented behavior.
**How to avoid:** Check `r.status_code == 400` before calling `r.raise_for_status()` — treat 400 as success indicating already-exists.
**Warning signs:** 500 errors on the game endpoint when testing with movies already in Radarr.

### Pitfall 2: Radarr `GET /api/v3/movie?tmdbId=X` Returns All Movies in Some Versions
**What goes wrong:** The `tmdbId` filter parameter on `GET /api/v3/movie` does not filter results in older Radarr versions — the endpoint returns the full collection.
**Why it happens:** GitHub issue #6086 documents this as a known Radarr bug that was patched but may exist in older installs.
**How to avoid:** When checking existence, filter the returned list in Python: `any(m["tmdbId"] == tmdb_id for m in r.json())` rather than checking `len(r.json()) > 0`.
**Warning signs:** `movie_exists` always returns True even for movies not in Radarr.

### Pitfall 3: React Router + nginx 404 on Page Refresh
**What goes wrong:** Navigating to `/game/123` directly returns 404 from nginx.
**Why it happens:** nginx serves static files; client-side routes don't exist on disk.
**How to avoid:** nginx.conf must have `try_files $uri $uri/ /index.html;` in the location block.
**Warning signs:** Direct URL access or browser refresh on any non-root route returns nginx 404.

### Pitfall 4: Tailwind v4 Breaks shadcn/ui
**What goes wrong:** shadcn/ui components render without styles or with broken dark mode.
**Why it happens:** shadcn/ui uses `@layer base { :root { --background: ... } }` pattern from `tailwind.config.js` theme extension; Tailwind v4 uses CSS `@theme` instead.
**How to avoid:** Pin `tailwindcss@3` in `package.json`. Do not upgrade to v4 during Phase 3.
**Warning signs:** shadcn components appear unstyled; dark mode toggle has no effect.

### Pitfall 5: `lazy="raise"` on All ORM Relationships
**What goes wrong:** `MissingGreenlet` or `sqlalchemy.exc.InvalidRequestError` when accessing a relationship inside an async session without loading it.
**Why it happens:** Phase 2 established `lazy="raise"` on all relationships.
**How to avoid:** Every query that traverses a relationship must use `selectinload()`. Check every game query: `selectinload(GameSession.steps)`, `selectinload(GameSessionStep.session)`.
**Warning signs:** Runtime error mentioning `greenlet_spawn` or `lazy="raise"` in traceback.

### Pitfall 6: One-Session-At-a-Time Not Enforced
**What goes wrong:** User starts two sessions; both show as "active"; state becomes incoherent.
**Why it happens:** No DB constraint — enforcement must be at API layer.
**How to avoid:** Before `INSERT INTO game_sessions`, query for any session with `status='active'` or `status='paused'`. If found, return 409.
**Warning signs:** Multiple rows in `game_sessions` with `status='active'`.

### Pitfall 7: Plex Webhook Fires During Paused Session
**What goes wrong:** A watch event for the paused session's chosen movie arrives via Plex webhook; session incorrectly advances.
**Why it happens:** The Plex webhook handler in `app/routers/plex.py` doesn't know about session state.
**How to avoid:** The Plex webhook handler must check for an active (non-paused) session matching the watched tmdb_id. Only call the game advancement hook when `session.status == 'active'`.
**Warning signs:** Session advances even when paused.

### Pitfall 8: Radarr Needs `rootFolderPath` and `qualityProfileId`
**What goes wrong:** `POST /api/v3/movie` returns 400 or 422 missing required fields.
**Why it happens:** The lookup result includes the full movie object but does NOT include `rootFolderPath` — that's a Radarr-internal configuration item.
**How to avoid:** Before adding, call `GET /api/v3/rootfolder` to retrieve the first configured root folder path. Cache this at startup on `app.state.radarr_client`. Similarly get `GET /api/v3/qualityprofile` for the first profile ID.
**Warning signs:** 400 errors from Radarr with body complaining about rootFolderPath or qualityProfileId.

---

## Code Examples

### Radarr Full Add Flow with Root Folder Fetch

```python
# Source: Radarr API v3 documented pattern (radarr.video/docs/api)
class RadarrClient:
    async def get_root_folder(self) -> str:
        r = await self._client.get("/api/v3/rootfolder")
        r.raise_for_status()
        folders = r.json()
        return folders[0]["path"] if folders else "/movies"

    async def get_quality_profile_id(self) -> int:
        r = await self._client.get("/api/v3/qualityprofile")
        r.raise_for_status()
        profiles = r.json()
        return profiles[0]["id"] if profiles else 1
```

### Session Advancement Hook in Plex Router

```python
# app/routers/plex.py — after storing WatchEvent, check for active session
async def _maybe_advance_session(tmdb_id: int, db: AsyncSession) -> None:
    result = await db.execute(
        select(GameSession).where(GameSession.status == "active")
    )
    session = result.scalar_one_or_none()
    if session and session.current_movie_tmdb_id == tmdb_id:
        # Session's chosen movie was just watched — mark session as "awaiting_continue"
        session.status = "awaiting_continue"
        await db.commit()
```

### TanStack React Query Session Polling

```typescript
// Poll for session state change when waiting for watch confirmation
const { data: session } = useQuery({
  queryKey: ['session', sessionId],
  queryFn: () => fetchSession(sessionId),
  refetchInterval: (data) =>
    data?.status === 'awaiting_continue' ? false : 5000,
})
```

### TMDB Poster URL

```typescript
// Standard TMDB image base URL — do not hand-roll this
const TMDB_IMG = "https://image.tmdb.org/t/p/w500"
const posterUrl = movie.poster_path
  ? `${TMDB_IMG}${movie.poster_path}`
  : "/placeholder-poster.svg"
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| pyarr for Radarr | Direct httpx.AsyncClient | pyarr last release July 2023 | pyarr is sync and unmaintained; httpx matches existing TMDBClient pattern |
| Tailwind v3 config.js | Tailwind v4 CSS @theme | Tailwind v4 released early 2025 | shadcn/ui NOT yet compatible with v4; pin v3 |
| React Router v5/v6 library mode | React Router v6 (library/SPA mode) | Stable | v7 adds framework mode complexity not needed here |
| Custom fetch in useEffect | @tanstack/react-query v5 | TanStack Query v5 (Nov 2023) | Eliminates loading/error boilerplate; handles mutation + cache invalidation |
| nginx static serve with route 404s | nginx + try_files fallback | Standard since React Router v4 | Required for SPA routing to work on page refresh |

**Deprecated/outdated:**
- `pyarr`: synchronous Requests-based library; last release July 2023; do not use in async FastAPI
- `Tailwind CSS v4` with shadcn/ui: incompatible until shadcn/ui explicitly supports v4 configuration
- `react-query` (old package name): now `@tanstack/react-query` v5; API changed significantly

---

## Open Questions

1. **Radarr `rootFolderPath` and `qualityProfileId` at startup**
   - What we know: These are required fields for `POST /api/v3/movie`; they are Radarr-instance-specific.
   - What's unclear: Whether to hardcode via env var or fetch dynamically from Radarr API.
   - Recommendation: Fetch from Radarr at `RadarrClient` startup (during lifespan) and cache on `app.state`. Use first returned value of each. This avoids adding new env vars and matches real-world Radarr config.

2. **Session advancement: polling vs WebSocket**
   - What we know: Frontend must detect when chosen movie is marked as watched. Plex webhook or manual mark can trigger this.
   - What's unclear: Whether to use polling or SSE/WebSocket.
   - Recommendation: 5-second polling with `refetchInterval` via react-query is the right choice for a 2-person home app. WebSocket adds backend complexity with no benefit for this use case.

3. **CSV TMDB disambiguation — vote_count tie-breaking edge case**
   - What we know: TMDB `/search/movie` returns multiple results for some titles; CONTEXT.md delegates to Claude's discretion; pick highest `vote_count`.
   - What's unclear: Whether to return an error or silently pick when there is a true tie.
   - Recommendation: Pick first result from `max(results, key=lambda m: m.get("vote_count", 0))` — TMDB orders results by relevance, so ties resolved by position.

4. **Runtime field on Movie model**
   - What we know: CONTEXT.md requires movie cards to display runtime. Runtime is NOT currently in the `Movie` ORM model (Phase 2 only stored title, year, poster_path, vote_average, genres).
   - What's unclear: Whether to add `runtime` column to `movies` table in Phase 3 migration or fetch on demand.
   - Recommendation: Add `runtime: Mapped[int | None]` to `Movie` model in Phase 3 Alembic migration. Fetch and populate from TMDB `/movie/{id}` response (field: `runtime`) when fetching full movie details. The column is nullable to handle cached stubs that pre-date Phase 3.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.3.4 + pytest-asyncio 0.24.0 |
| Config file | `backend/pytest.ini` (exists; `asyncio_mode = auto`) |
| Quick run command | `cd backend && pytest tests/test_game.py -x -q` |
| Full suite command | `cd backend && pytest -x -q` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| GAME-01 | POST /game/sessions creates session with start movie | unit | `pytest tests/test_game.py::test_create_session -x` | Wave 0 |
| GAME-01 | POST /game/sessions returns 409 if active session exists | unit | `pytest tests/test_game.py::test_create_session_conflict -x` | Wave 0 |
| GAME-02 | GET /game/sessions/{id}/eligible-actors excludes picked actors | unit | `pytest tests/test_game.py::test_eligible_actors_excludes_picked -x` | Wave 0 |
| GAME-03 | GET /game/sessions/{id}/eligible-movies returns unwatched filmography | unit | `pytest tests/test_game.py::test_eligible_movies -x` | Wave 0 |
| GAME-04 | POST /game/sessions/{id}/pick-actor records actor and excludes on next call | unit | `pytest tests/test_game.py::test_pick_actor_persisted -x` | Wave 0 |
| GAME-05 | Sort by rating/genre/runtime returns correctly ordered results | unit | `pytest tests/test_game.py::test_sort_movies -x` | Wave 0 |
| GAME-06 | Toggle all_movies flag returns watched+unwatched with badge | unit | `pytest tests/test_game.py::test_all_movies_toggle -x` | Wave 0 |
| GAME-07 | Watched movie is returned with selectable=False | unit | `pytest tests/test_game.py::test_watched_not_selectable -x` | Wave 0 |
| GAME-08 | POST /game/sessions/{id}/request-movie triggers Radarr add | unit (mocked Radarr) | `pytest tests/test_game.py::test_request_movie_radarr -x` | Wave 0 |
| GAME-08 | Radarr skipped when movie already exists | unit (mocked Radarr) | `pytest tests/test_game.py::test_request_movie_skip_radarr -x` | Wave 0 |

Frontend tests are out of scope for the backend pytest suite — no Vitest/Jest setup is planned for Phase 3 (TV/tablet UI with small team; manual verification is the test strategy for the React layer).

### Sampling Rate
- **Per task commit:** `cd backend && pytest tests/test_game.py -x -q`
- **Per wave merge:** `cd backend && pytest -x -q`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `backend/tests/test_game.py` — all GAME-01 through GAME-08 test stubs
- [ ] `backend/tests/test_radarr.py` — RadarrClient unit tests (mocked httpx)

---

## Sources

### Primary (HIGH confidence)
- Existing codebase: `backend/app/models/__init__.py`, `backend/app/services/tmdb.py`, `backend/app/routers/actors.py`, `backend/app/routers/movies.py`, `backend/app/routers/plex.py` — established patterns directly verified
- `backend/requirements.txt` — exact library versions confirmed
- `backend/pytest.ini` — test configuration confirmed
- `ui.shadcn.com/docs/installation/vite` — Vite + shadcn/ui installation steps verified
- Radarr OpenAPI spec (github.com/Radarr/Radarr/develop/src/Radarr.Api.V3/openapi.json) — endpoint structures verified

### Secondary (MEDIUM confidence)
- pyarr PyPI page (pypi.org/project/pyarr/) — confirmed version 5.2.0, last release July 2023, synchronous library
- Radarr GitHub issues #6086 (tmdbId filter bug), #7095 (400 on duplicate) — verified through search
- TanStack Query npm page — confirmed v5.90.x current, React 18/19 compatible
- Tailwind CSS v3/v4 shadcn/ui incompatibility — verified through shadcn/ui community documentation

### Tertiary (LOW confidence)
- Radarr `rootFolderPath` + `qualityProfileId` fetch-at-startup recommendation — based on Radarr community patterns; verify against actual Radarr API response on target installation
- nginx `try_files` requirement for SPA routing — standard knowledge; verify against actual Dockerfile behavior during implementation

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all backend libraries already in project; frontend stack confirmed via official shadcn docs
- Architecture: HIGH — game session schema design and Radarr flow based on direct code reading + Radarr API research
- Pitfalls: HIGH for backend patterns (directly from codebase); MEDIUM for Radarr-specific quirks (from verified GitHub issues)

**Research date:** 2026-03-15
**Valid until:** 2026-04-15 (stable libraries; Radarr API rarely breaks; shadcn/ui v4 compat may change)
