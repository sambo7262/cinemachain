# Phase 04: Caching, UI/UX Polish, and Session Management — Research

**Researched:** 2026-03-17
**Domain:** APScheduler (FastAPI in-process), TMDB bulk fetch, React notification patterns, shadcn Dialog, responsive Tailwind layout, destructive session actions
**Confidence:** HIGH — all findings grounded in direct codebase inspection; no speculative claims

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- APScheduler runs in-process inside FastAPI container — auto-starts with Docker, no external setup
- Nightly at 3am (default), configurable via `TMDB_CACHE_TIME=03:00` in .env
- Top-N movies configurable via `TMDB_CACHE_TOP_N=5000` in .env (default 5000)
- Incremental add-only — skip movies already in DB (by `fetched_at` presence), never purge
- Radarr notification: slim full-width banner rendered immediately below the global NavBar; never overlaps game controls
- Radarr notification text: "Already in Radarr" / "Movie Queued for Download" — no other variants
- Radarr notification: auto-dismiss after 5 seconds; manually dismissible via × button before that
- Session Home poster: large hero poster (~120px wide) left-anchored; previous movie is text-only
- Fallback when `poster_path` is null: grey placeholder rectangle at the same dimensions
- Delete last step: confirm dialog (shadcn Dialog, not `window.confirm`) required before executing
- On confirm: remove most recent step, revert `current_movie_tmdb_id` and `current_movie_watched` to prior state; no Radarr cancellation
- Delete archived session: confirm dialog required before executing; permanent DB removal of session and all its steps
- `⋯` actions menu on session home houses: Delete last step, Export CSV, (Archive session)
- Suggestions tab: "Suggested" alongside Eligible Actors / Eligible Movies — always top 5
- Suggestions ranking: genre-weighted by watch history (session steps + WatchEvents), tie-broken by TMDB rating (500-vote floor)
- Suggestion candidates: only movies reachable via currently eligible actors
- Each suggestion shows "via [Actor Name]" + full movie card detail set
- Watch History tab removed from GameLobby — retain "Search Title" and "Import Chain" only
- Movie cards: MPAA + runtime + genre + TMDB rating always visible (no hover/expansion)
- Filter sidebar: persistent on desktop, collapses to toggle button on mobile
- App max-width: 1400px centered; applied at root layout wrapper, not per-page
- Delete actions: use shadcn Dialog for confirmation
- New env vars `TMDB_CACHE_TOP_N` and `TMDB_CACHE_TIME` documented in `.env.example`
- Movie stubs from CSV import enriched with runtime/genre via lazy enrichment

### Claude's Discretion
- Mobile breakpoints and exact responsive behavior (column count, spacing, etc.)
- Poster placeholder styling (grey rectangle dimensions, border radius)
- Genre tag chip styling on movie cards
- Session actions menu component (dropdown, popover, or sheet)
- APScheduler job retry behavior on TMDB rate limit hit during nightly run
- Exact sidebar width and layout proportions within the 1400px cap

### Deferred Ideas (OUT OF SCOPE)
- Manual cache trigger via UI button or HTTP endpoint
- Radarr download cancellation when deleting a session step
- Movie suggestion count beyond 5 / pagination — fixed at 5
- Cross-session suggestion history
- Full-width no-cap layout
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| CACHE-01 | Nightly job pre-populates top ~5000 movies by vote count so no mainstream film triggers on-demand TMDB call | APScheduler wired in `main.py` lifespan; reuses `_ensure_movie_cast_in_db` + `_ensure_movie_details_in_db`; TMDB `/discover/movie` sorted by `vote_count.desc` pages through top-N |
| CACHE-02 | Movie stubs from CSV import have runtime and genre data populated (lazy enrichment) | `_ensure_movie_details_in_db` already exists and handles `genres IS NULL` rows; nightly job calls this for all cached movies; CSV stubs get enriched on next nightly run |
| UX-06 | Radarr notification appears in consistent, unobtrusive position below NavBar and does not overlap game controls | Current `radarrStatus` state in `GameSession.tsx` at lines 410–422; must lift state to React Context or a notification store and mount banner below NavBar in `App.tsx` |
| UX-07 | Session home page displays active movie's poster thumbnail | `StepResponse` already carries `poster_path`; `GameSessionDTO.steps[0].poster_path` available; hero poster uses `w185` TMDB image size |
| UX-08 | Actor and movie images load correctly at every step of the session journey | `_enrich_steps_thumbnails` already populates `poster_path` and `profile_path` on all steps; chain history and eligible actors already use TMDB image URLs |
| UX-09 | Filter sidebar persistent on desktop, toggle on mobile; movie cards show MPAA + runtime + genre + TMDB rating | `MovieFilterSidebar` already collapsible; refactor to CSS-driven persistent vs. mobile toggle; `MovieCard` already renders these fields — MPAA badge missing, needs addition |
| SESSION-01 | User can delete the last step of a session to go one move backwards | New `DELETE /sessions/{id}/steps/last`; removes highest `step_order` step; resets `current_movie_tmdb_id` and `current_movie_watched` to prior step values |
| SESSION-02 | Archived sessions can be permanently deleted from DB | New `DELETE /sessions/{id}`; hard delete; guard with `status == "archived"` check |
</phase_requirements>

---

## Summary

Phase 4 has three distinct tracks: backend scheduler/cache, frontend UI polish, and session management endpoints. All three tracks can be planned and executed largely independently.

The backend track introduces APScheduler as the one genuinely new dependency — it is not yet in `requirements.txt` or anywhere in the codebase. All enrichment helpers (`_ensure_movie_cast_in_db`, `_ensure_movie_details_in_db`, `_ensure_actor_credits_in_db`) already exist in `game.py` and are proven in production; the nightly job is a loop that calls these helpers for each TMDB ID returned by the discovery endpoint.

The frontend track has several distinct sub-tasks: lifting the Radarr notification out of `GameSession.tsx` into a shared context, adding a poster to the Now Playing card, adding a `shadcn Dialog` component (which does not yet exist in `frontend/src/components/ui/`), creating the `⋯` actions menu, removing the Watch History tab, building the Suggestions tab, refactoring the filter sidebar to persistent-on-desktop, and widening the layout to 1400px. The movie card and DTO already have all required fields — no new DTO changes are needed.

The session management track adds two new backend endpoints and wires their confirmation dialogs in the frontend.

**Primary recommendation:** Plan wave 0 to create the Dialog component and APScheduler install, then parallelize the three tracks in waves — they share no blocking dependencies after wave 0.

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| APScheduler | 3.x (AsyncScheduler API) | In-process background scheduler wired to FastAPI lifespan | Only scheduler that integrates cleanly with asyncio and FastAPI lifespan without a separate worker process |
| FastAPI | 0.115.6 (installed) | Backend framework | Already in use |
| SQLAlchemy asyncio | 2.0.36 (installed) | Async ORM | Already in use |
| React 18 | 18.3.1 (installed) | Frontend | Already in use |
| TanStack Query | 5.x (installed) | Data fetching + cache invalidation | Already in use |
| Tailwind CSS | 3.4.19 (installed) | Styling and responsive layout | Already in use |
| shadcn/ui (manual) | — | UI primitives | Established pattern — written manually in this project |
| @radix-ui/react-dialog | ^1.x | Dialog primitive for shadcn Dialog | Radix UI is the underlying primitive layer already used for all other shadcn components |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| asyncio.Semaphore | stdlib | TMDB rate limit control during nightly bulk fetch | Already in TMDBClient (`self._sem`) — reuse |
| lucide-react | 0.577.0 (installed) | Icons (MoreHorizontal for `⋯` menu) | Already used throughout |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| APScheduler in-process | Celery Beat + Redis | Celery requires a separate broker container — overkill for a single nightly job on a NAS |
| APScheduler in-process | FastAPI BackgroundTasks triggered by a cron container | Adds infra complexity; APScheduler is simpler for time-based schedules |
| React Context for notification | Zustand or Jotai | Overkill for one notification slot; React Context is sufficient |

**Installation:**
```bash
# Backend
pip install apscheduler>=3.10.0

# Frontend
npm install @radix-ui/react-dialog
```

---

## Architecture Patterns

### Recommended Project Structure (changes only)

```
backend/
├── app/
│   ├── main.py                    # APScheduler wired here in lifespan
│   ├── settings.py                # TMDB_CACHE_TOP_N, TMDB_CACHE_TIME added
│   ├── services/
│   │   └── cache.py               # NEW: nightly_cache_job() function
│   └── routers/
│       └── game.py                # 2 new DELETE endpoints
frontend/src/
├── App.tsx                        # Layout: max-w-[1400px], notification context, Radarr banner
├── contexts/
│   └── NotificationContext.tsx    # NEW: global Radarr notification state
├── components/
│   ├── RadarrBanner.tsx           # NEW: banner below NavBar
│   ├── ui/
│   │   └── dialog.tsx             # NEW: shadcn Dialog primitive
│   └── MovieFilterSidebar.tsx     # Refactored: persistent desktop / mobile toggle
├── pages/
│   ├── GameSession.tsx            # Actions menu, poster thumbnail, suggestions tab, lift radarrStatus
│   ├── GameLobby.tsx              # Remove Watch History tab
│   └── ArchivedSessions.tsx       # Delete button + Dialog confirmation
```

### Pattern 1: APScheduler AsyncScheduler in FastAPI lifespan

**What:** APScheduler 3.x `AsyncScheduler` started and stopped inside the FastAPI `@asynccontextmanager lifespan`. The scheduler uses an `AsyncIOScheduler` with a `CronTrigger`.

**When to use:** Any in-process time-based background job that needs the same asyncio event loop as the FastAPI app.

**Example:**
```python
# backend/app/main.py (updated lifespan)
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from app.services.cache import nightly_cache_job

@asynccontextmanager
async def lifespan(app: FastAPI):
    # ... existing DB, TMDB, Radarr init ...

    # Parse TMDB_CACHE_TIME="03:00" into hour/minute
    cache_time_parts = settings.tmdb_cache_time.split(":")
    cache_hour = int(cache_time_parts[0])
    cache_minute = int(cache_time_parts[1])

    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        nightly_cache_job,
        trigger=CronTrigger(hour=cache_hour, minute=cache_minute),
        kwargs={"tmdb": app.state.tmdb_client, "top_n": settings.tmdb_cache_top_n},
        id="nightly_tmdb_cache",
        replace_existing=True,
        misfire_grace_time=3600,  # allow up to 1hr late start (NAS restarts)
    )
    scheduler.start()
    app.state.scheduler = scheduler

    yield

    scheduler.shutdown(wait=False)
    await app.state.tmdb_client.close()
    await app.state.radarr_client.close()
    await engine.dispose()
```

**Note on APScheduler version:** APScheduler 3.x uses `AsyncIOScheduler`. APScheduler 4.x introduced a new async API (`AsyncScheduler`). Install `apscheduler>=3.10,<4` to stay on the 3.x API that matches the pattern above, or install `>=4.0` and use the new `AsyncScheduler` + `async with AsyncScheduler() as scheduler`. Either works — the 3.x API is more stable for this use case.

### Pattern 2: Nightly Cache Job — Incremental Discovery Fetch

**What:** `nightly_cache_job()` in `services/cache.py` pages through TMDB `/discover/movie` sorted by `vote_count.desc`, collects the top-N TMDB IDs, then calls existing `_ensure_*` helpers for each movie not already fully cached.

**When to use:** The nightly scheduler job only.

**Example:**
```python
# backend/app/services/cache.py
async def nightly_cache_job(tmdb: TMDBClient, top_n: int = 5000) -> None:
    """Fetch top-N movies by vote count and ensure all are in the DB."""
    logger.info("nightly_cache_job starting: top_n=%d", top_n)
    page = 1
    collected: list[int] = []

    while len(collected) < top_n:
        try:
            r = await tmdb._client.get(
                "/discover/movie",
                params={
                    "sort_by": "vote_count.desc",
                    "vote_count.gte": 500,     # 500-vote floor matches game eligibility
                    "page": page,
                },
            )
            r.raise_for_status()
        except Exception as e:
            logger.error("TMDB discover fetch failed on page %d: %s", page, e)
            break

        results = r.json().get("results", [])
        if not results:
            break
        collected.extend(item["id"] for item in results)
        page += 1

    tmdb_ids = collected[:top_n]
    logger.info("nightly_cache_job: %d movie IDs collected", len(tmdb_ids))

    async with _bg_session_factory() as db:
        # Only process movies not already fully cached (fetched_at IS NOT NULL + genres IS NOT NULL)
        already_cached = await db.execute(
            select(Movie.tmdb_id).where(
                Movie.tmdb_id.in_(tmdb_ids),
                Movie.fetched_at.isnot(None),
                Movie.genres.isnot(None),
            )
        )
        cached_ids = {row[0] for row in already_cached.all()}
        to_fetch = [tid for tid in tmdb_ids if tid not in cached_ids]
        logger.info("nightly_cache_job: %d movies need enrichment", len(to_fetch))

        for tmdb_id in to_fetch:
            await _ensure_movie_cast_in_db(tmdb_id, tmdb, db)
            await _ensure_movie_details_in_db([tmdb_id], tmdb, db)
            # Small sleep to avoid TMDB rate limit (40 req/s per TMDB docs)
            await asyncio.sleep(0.05)

    logger.info("nightly_cache_job complete")
```

**Key insight:** `_ensure_movie_cast_in_db` and `_ensure_movie_details_in_db` are imported from `game.py` or moved to a shared `services/` location. The helpers are already idempotent (on_conflict_do_nothing / on_conflict_do_update), so repeated runs are safe.

**Import caveat:** `_ensure_movie_cast_in_db` and `_ensure_movie_details_in_db` are currently defined inside `routers/game.py`. Options:
1. Move them to `services/cache.py` and import into both `game.py` and the nightly job (cleanest)
2. Import them directly from `routers/game.py` into `services/cache.py` (works but creates cross-layer import)

**Recommended:** Move shared helpers to `services/cache.py`. The router imports them from there.

### Pattern 3: Global Radarr Notification Context

**What:** Lift `radarrStatus` out of `GameSession.tsx` into a React Context so the banner can be mounted in `App.tsx` below `NavBar`, independent of the current route.

**When to use:** Any notification that must survive route changes or mount above page-level components.

**Example:**
```typescript
// frontend/src/contexts/NotificationContext.tsx
import { createContext, useContext, useState, useCallback, useRef } from "react"

interface NotificationContextValue {
  radarrMessage: string | null
  showRadarr: (msg: string) => void
  dismissRadarr: () => void
}

const NotificationContext = createContext<NotificationContextValue | null>(null)

export function NotificationProvider({ children }: { children: React.ReactNode }) {
  const [radarrMessage, setRadarrMessage] = useState<string | null>(null)
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  const showRadarr = useCallback((msg: string) => {
    if (timerRef.current) clearTimeout(timerRef.current)
    setRadarrMessage(msg)
    timerRef.current = setTimeout(() => setRadarrMessage(null), 5000)
  }, [])

  const dismissRadarr = useCallback(() => {
    if (timerRef.current) clearTimeout(timerRef.current)
    setRadarrMessage(null)
  }, [])

  return (
    <NotificationContext.Provider value={{ radarrMessage, showRadarr, dismissRadarr }}>
      {children}
    </NotificationContext.Provider>
  )
}

export function useNotification() {
  const ctx = useContext(NotificationContext)
  if (!ctx) throw new Error("useNotification must be used within NotificationProvider")
  return ctx
}
```

```typescript
// App.tsx — mount banner between NavBar and Routes
<NotificationProvider>
  <div className="min-h-screen bg-background text-foreground">
    <NavBar />
    <RadarrBanner />   {/* reads from context, renders if message present */}
    <div className="max-w-[1400px] mx-auto px-4 sm:px-6 lg:px-8">
      <Routes>...</Routes>
    </div>
  </div>
</NotificationProvider>
```

**Migration in GameSession.tsx:** Replace the `radarrStatus` useState + the useEffect fallback with `const { showRadarr } = useNotification()`. Call `showRadarr("Already in Radarr")` or `showRadarr("Movie Queued for Download")` in the `requestMovie` mutation `onSuccess`.

### Pattern 4: shadcn Dialog (manual write — no CLI)

**What:** The project writes shadcn components manually (established pattern — see STATE.md). `@radix-ui/react-dialog` is the primitive.

**When to use:** All confirmation dialogs in Phase 4 (delete last step, delete archived session, any future destructive actions).

**Example:**
```typescript
// frontend/src/components/ui/dialog.tsx
import * as DialogPrimitive from "@radix-ui/react-dialog"
import { X } from "lucide-react"
import { cn } from "@/lib/utils"

const Dialog = DialogPrimitive.Root
const DialogTrigger = DialogPrimitive.Trigger
const DialogPortal = DialogPrimitive.Portal
const DialogClose = DialogPrimitive.Close

const DialogOverlay = ({ className, ...props }: React.ComponentPropsWithoutRef<typeof DialogPrimitive.Overlay>) => (
  <DialogPrimitive.Overlay
    className={cn("fixed inset-0 z-50 bg-black/80 data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0", className)}
    {...props}
  />
)

const DialogContent = ({ className, children, ...props }: React.ComponentPropsWithoutRef<typeof DialogPrimitive.Content>) => (
  <DialogPortal>
    <DialogOverlay />
    <DialogPrimitive.Content
      className={cn(
        "fixed left-[50%] top-[50%] z-50 grid w-full max-w-lg translate-x-[-50%] translate-y-[-50%] gap-4 border border-border bg-background p-6 shadow-lg duration-200 data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0 data-[state=closed]:zoom-out-95 data-[state=open]:zoom-in-95 data-[state=closed]:slide-out-to-left-1/2 data-[state=open]:slide-in-from-left-1/2 rounded-lg",
        className,
      )}
      {...props}
    >
      {children}
      <DialogClose className="absolute right-4 top-4 rounded-sm opacity-70 ring-offset-background transition-opacity hover:opacity-100 focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2">
        <X className="h-4 w-4" />
        <span className="sr-only">Close</span>
      </DialogClose>
    </DialogPrimitive.Content>
  </DialogPortal>
)

const DialogHeader = ({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) => (
  <div className={cn("flex flex-col space-y-1.5 text-center sm:text-left", className)} {...props} />
)

const DialogTitle = ({ className, ...props }: React.ComponentPropsWithoutRef<typeof DialogPrimitive.Title>) => (
  <DialogPrimitive.Title className={cn("text-lg font-semibold leading-none tracking-tight", className)} {...props} />
)

const DialogDescription = ({ className, ...props }: React.ComponentPropsWithoutRef<typeof DialogPrimitive.Description>) => (
  <DialogPrimitive.Description className={cn("text-sm text-muted-foreground", className)} {...props} />
)

export { Dialog, DialogTrigger, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogClose }
```

**Usage pattern:**
```typescript
<Dialog open={confirmOpen} onOpenChange={setConfirmOpen}>
  <DialogContent>
    <DialogHeader>
      <DialogTitle>Delete last step?</DialogTitle>
      <DialogDescription>This cannot be undone.</DialogDescription>
    </DialogHeader>
    <div className="flex justify-end gap-2">
      <Button variant="outline" onClick={() => setConfirmOpen(false)}>Cancel</Button>
      <Button variant="destructive" onClick={handleDeleteLastStep}>Delete</Button>
    </div>
  </DialogContent>
</Dialog>
```

### Pattern 5: Delete Last Step — Backend Logic

**What:** `DELETE /sessions/{id}/steps/last` removes the highest `step_order` step and resets session state to the second-highest step.

**Key logic:**
```python
@router.delete("/sessions/{session_id}/steps/last", status_code=200)
async def delete_last_step(session_id: int, db: AsyncSession = Depends(get_db)):
    session = await db.get(GameSession, session_id, options=[selectinload(GameSession.steps)])
    if session is None or session.status == "archived":
        raise HTTPException(404)

    steps = sorted(session.steps, key=lambda s: s.step_order)
    if len(steps) == 0:
        raise HTTPException(400, "No steps to delete")

    last_step = steps[-1]
    await db.delete(last_step)

    # Revert session to previous movie
    if len(steps) >= 2:
        prev_step = steps[-2]
        session.current_movie_tmdb_id = prev_step.movie_tmdb_id
        session.current_movie_watched = False  # revert to unwatched state

    session.status = "active"  # in case it was awaiting_continue
    await db.commit()
    # ... rebuild and return session response
```

**Edge case:** If the session has only 1 step and it is deleted, the session becomes invalid. The plan should decide: either prevent deletion when only 1 step remains (raise 400), or allow it and set session to "ended". The CONTEXT.md does not specify — leave this as a planning decision; recommend blocking deletion when only 1 step remains.

### Pattern 6: Suggestions Endpoint

**What:** `GET /sessions/{id}/suggestions` returns top 5 movies reachable via currently eligible actors, ranked by genre affinity + TMDB rating.

**Algorithm:**
1. Fetch eligible actors for the session (reuse `get_eligible_actors` logic)
2. For each eligible actor, fetch their `Credit` rows → collect candidate movie tmdb_ids
3. Exclude already-picked movies (from session steps)
4. Score each candidate: genre overlap with watch history genres (WatchEvents + session steps), tie-break by `vote_average`
5. Apply 500-vote floor (`vote_count >= 500`)
6. Return top 5 as `EligibleMovieDTO` with `via_actor_name` populated

**Watch history genre source:** `WatchEvent.tmdb_id` → join to `Movie.genres` → parse JSON genre list → frequency count.

### Anti-Patterns to Avoid
- **Calling TMDB synchronously in the nightly job without rate limiting:** The existing `TMDBClient._sem = asyncio.Semaphore(10)` already caps concurrent requests. The nightly job must use the same semaphore — pass `tmdb` (the shared `TMDBClient` instance) to the job, do not create a new client.
- **Using `window.confirm` for delete confirmations:** STATE.md confirms this was acceptable in earlier phases but Phase 4 explicitly requires shadcn Dialog.
- **Mounting the Radarr banner inside `GameSession.tsx`:** The entire point of UX-06 is that the banner renders below NavBar regardless of which component called it — it must live in `App.tsx`.
- **Creating a new `_bg_session_factory` in cache.py:** The factory already exists in `game.py` — move to `db.py` or import from `game.py` to avoid duplication.
- **Hard-deleting a session in any status other than "archived":** The endpoint must guard with `status == "archived"` — a misfire on an active session destroys gameplay state.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| In-process cron scheduling | Custom asyncio task + sleep loop | APScheduler `AsyncIOScheduler` + `CronTrigger` | Handles misfire grace time, NAS restarts, timezone-aware scheduling; sleep loops break on event loop restart |
| Modal confirmation dialog | `window.confirm` or custom div-overlay | shadcn Dialog (Radix primitive) | Accessibility, focus trap, keyboard dismiss, animation — all handled by Radix |
| Notification timeout management | Custom `setTimeout` in component | `useCallback` + `useRef` in Context provider | Prevents timer leak on remount, clears on dismiss, survives route changes |
| Genre affinity scoring | Full ML ranking | Frequency count over WatchEvent genres + vote_average tie-break | Sufficient signal for top-5 suggestions; avoid over-engineering |

---

## Common Pitfalls

### Pitfall 1: `_bg_session_factory` in the nightly job must use the shared engine

**What goes wrong:** If `cache.py` instantiates its own `async_sessionmaker(engine)`, it imports `engine` from `db.py`. If `game.py` also creates `_bg_session_factory = async_sessionmaker(engine)`, there are two factories for the same engine — this is fine (same underlying engine object), but the factories are duplicated. The nightly job's DB sessions are independent of the request session pool.

**Why it happens:** `_bg_session_factory` is currently defined at module level in `game.py`. When the job is extracted to `services/cache.py`, it needs its own factory or imports the one from `game.py`.

**How to avoid:** Define `_bg_session_factory` once in `app/db.py` alongside `engine` and `get_db`. Import it in both `game.py` and `cache.py`.

### Pitfall 2: APScheduler timezone and NAS clock

**What goes wrong:** `CronTrigger(hour=3, minute=0)` uses the system timezone. On the Synology NAS, the TZ may be UTC or Asia/Pacific depending on DSM settings. The nightly job could fire at 3am UTC = wrong local time.

**Why it happens:** APScheduler defaults to local timezone; Docker containers often run UTC.

**How to avoid:** Pass explicit `timezone="UTC"` to `CronTrigger` and document this in `.env.example` with a comment. If the user is in Pacific time, 3am UTC = 7pm local — fine for a nightly cache job. Alternatively, expose `TMDB_CACHE_TIMEZONE` env var (Claude's discretion).

### Pitfall 3: Radarr notification state survives across route changes (good) but must not fire on initial session load

**What goes wrong:** The current `radarrFallbackFiredRef` guard in `GameSession.tsx` prevents re-firing on re-render, but when state is lifted to Context, the message persists across navigation. If a user navigates to a session that already has a `radarr_status` from a previous request, the banner could fire incorrectly.

**Why it happens:** The fallback `useEffect` reads `session.radarr_status` from the DB-persisted field, not from the just-fired Radarr call.

**How to avoid:** The Context `showRadarr()` should only be called from the `requestMovie` mutation `onSuccess` callback — not from any `useEffect` reading `session.radarr_status`. Remove the fallback `useEffect` entirely once the Context is in place.

### Pitfall 4: `DELETE /sessions/{id}` endpoint conflicts with existing `GET /sessions/{id}` route ordering

**What goes wrong:** FastAPI matches routes in order. A `DELETE /sessions/{session_id}` route must be registered after all static sub-path routes (`/sessions/active`, `/sessions/archived`, `/sessions/import-csv`) to prevent string-as-integer 422 errors.

**Why it happens:** Same issue that required placing `GET /sessions/{session_id}` after `/sessions/active` (STATE.md: 03.1-08 decision).

**How to avoid:** Register `DELETE /sessions/{session_id}` as the last route in the session group, after all static paths.

### Pitfall 5: `_ensure_movie_cast_in_db` currently sets `fetched_at=datetime.utcnow()` on initial Movie stub

**What goes wrong:** The nightly cache job uses `fetched_at IS NOT NULL` as the "already cached" signal to skip movies. But `_ensure_movie_cast_in_db` sets `fetched_at` on the stub row even when the movie has not yet had `_ensure_movie_details_in_db` run for genres/runtime. This means the incremental skip check must use `genres IS NOT NULL` rather than just `fetched_at IS NOT NULL`.

**Why it happens:** `fetched_at` was designed as "we have attempted a cast fetch" not "we have full genre+runtime data."

**How to avoid:** The nightly job's already-cached filter must require BOTH `fetched_at IS NOT NULL` AND `genres IS NOT NULL` — which matches the example in Pattern 2 above.

### Pitfall 6: `@radix-ui/react-dialog` not yet installed

**What goes wrong:** The `dialog.tsx` component file will fail at import — `@radix-ui/react-dialog` is absent from `package.json`.

**Why it happens:** The Dialog shadcn component was not included in Phase 03.2 because `window.confirm` was the accepted fallback.

**How to avoid:** Wave 0 plan installs `@radix-ui/react-dialog` via `npm install @radix-ui/react-dialog` and writes `dialog.tsx`. All subsequent plans that use Dialog depend on Wave 0.

### Pitfall 7: Filter sidebar refactor breaks existing GameSession layout

**What goes wrong:** `MovieFilterSidebar` is currently a standalone `w-56 shrink-0` component rendered alongside the movie grid inside the Eligible Movies `TabsContent`. The persistent desktop sidebar needs a flex row wrapper. If the wrapper is added only inside `GameSession.tsx`, the layout will not apply to future pages that use the same sidebar.

**Why it happens:** The sidebar component does not own its layout context.

**How to avoid:** Keep the sidebar component unchanged (still renders its own `w-56` box). Add a responsive wrapper div in `GameSession.tsx` Eligible Movies tab: `flex flex-col md:flex-row gap-4`. The sidebar is `hidden md:block` by default; a "Filters" button above the grid toggles it on mobile.

---

## Code Examples

Verified patterns from codebase inspection:

### Existing `_ensure_movie_details_in_db` signature (reused by nightly job)
```python
# Source: backend/app/routers/game.py lines 427–449
async def _ensure_movie_details_in_db(
    tmdb_ids: list[int],
    tmdb: TMDBClient,
    db: AsyncSession,
) -> None:
    """Fetches full movie details (genres + runtime) for movies missing genre data."""
    # Already handles genres IS NULL filter internally
    # Errors swallowed per-movie — safe to call in batch
```

### Existing TMDB image URL patterns
```typescript
// Source: frontend/src/components/MovieCard.tsx line 20
const TMDB_IMG = "https://image.tmdb.org/t/p/w342"  // used in eligible movie grid

// Session Home hero poster — use larger size:
const HERO_IMG = "https://image.tmdb.org/t/p/w185"

// Actor thumbnails — already in GameSession.tsx line 496:
src={`https://image.tmdb.org/t/p/w92${actor.profile_path}`}
```

### Existing `_build_session_response` — no changes needed for delete-last-step response
```python
# Source: backend/app/routers/game.py lines 219–261
# _build_session_response already handles all enrichment.
# delete_last_step endpoint calls the same helper after DB mutation.
```

### Session Home Now Playing card — current structure (lines 329–394)
```typescript
// Source: frontend/src/pages/GameSession.tsx
// Current: text-only Now Playing card
// Phase 4: add poster image to left of currentStep text
// poster_path is available on currentStep (StepResponse already carries poster_path)
const poster = currentStep?.poster_path
  ? `https://image.tmdb.org/t/p/w185${currentStep.poster_path}`
  : null
// Render: flex row with poster on left (~120px), text block on right
```

### `EligibleMovieDTO` — no new fields needed for Suggestions tab
```typescript
// Source: frontend/src/lib/api.ts lines 57–70
// via_actor_name: string | null  ← already present
// All required fields already in DTO
// New endpoint type: GET /sessions/{id}/suggestions returns EligibleMovieDTO[]
```

### GameLobby Watch History tab removal
```typescript
// Source: frontend/src/pages/GameLobby.tsx line 302
// Current: grid-cols-3 with "Watch History", "Search Title", "Import Chain"
// Change to: grid-cols-2 with "Search Title", "Import Chain" only
// Remove: TabsTrigger value="watched", TabsContent value="watched", watchedMovies query
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `window.confirm` for destructive actions | shadcn Dialog (Radix) | Phase 4 | Accessible, styled, keyboard-navigable |
| Radarr status as local component state | React Context notification | Phase 4 | Banner persists across route changes, renders below NavBar |
| Collapsible sidebar on all screen sizes | Persistent desktop sidebar / toggle on mobile | Phase 4 | Consistent filter access without extra clicks on desktop |
| On-demand TMDB fetch for every mainstream movie | Nightly pre-cached top 5000 | Phase 4 | Eliminates latency for 95%+ of typical game sessions |

**Deprecated/outdated in this phase:**
- `window.confirm` in GameSession: replaced by shadcn Dialog
- Watch History tab in GameLobby: removed — no replacement, tabs reduce to 2
- `radarrStatus` useState in `GameSession.tsx`: replaced by Context notification
- Narrow `max-w-2xl` (or similar) container: replaced by `max-w-[1400px]`

---

## Open Questions

1. **Single-step delete behavior**
   - What we know: CONTEXT.md says delete last step reverts to prior state
   - What's unclear: What happens if there is only 1 step (the starting movie step)?
   - Recommendation: Block the action with a 400 response and disable the "Delete last step" menu item in the frontend when `session.steps.length <= 1`

2. **APScheduler version (3.x vs 4.x)**
   - What we know: APScheduler 3.x uses `AsyncIOScheduler`; 4.x uses `AsyncScheduler` with a different async context manager API
   - What's unclear: which version pip will resolve without a pinned version
   - Recommendation: Pin `apscheduler>=3.10.4,<4.0` in requirements.txt to avoid 4.x API changes

3. **`_bg_session_factory` ownership**
   - What we know: Currently defined in `routers/game.py` line 22
   - What's unclear: Whether to move it to `db.py` or duplicate in `services/cache.py`
   - Recommendation: Move to `app/db.py` alongside `engine` and `get_db`; import in both modules

4. **Suggestions tab: what if fewer than 5 actionable suggestions exist?**
   - What we know: CONTEXT.md says "always top 5"
   - What's unclear: Behavior when candidate pool has fewer than 5 eligible movies
   - Recommendation: Return however many candidates exist (up to 5); show "No suggestions available" if 0

---

## Validation Architecture

No `workflow.nyquist_validation` key in `.planning/config.json` — treating as enabled.

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.3.4 + pytest-asyncio 0.24.0 |
| Config file | `backend/pytest.ini` (or `backend/pyproject.toml` — check) |
| Quick run command | `cd backend && pytest tests/test_game.py -x -q` |
| Full suite command | `cd backend && pytest -x -q` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| CACHE-01 | Nightly job fetches top-N movies and inserts into DB | unit | `pytest tests/test_cache.py -x -q` | Wave 0 |
| CACHE-02 | Movies with `genres IS NULL` get enriched after job runs | unit | `pytest tests/test_cache.py::test_enrichment -x` | Wave 0 |
| UX-06 | Radarr notification text matches exact strings | manual-only | — | n/a |
| UX-07 | Session home poster renders poster thumbnail | manual-only | — | n/a |
| UX-08 | Actor/movie images load correctly | manual-only | — | n/a |
| UX-09 | Filter sidebar persistent desktop / toggle mobile | manual-only | — | n/a |
| SESSION-01 | DELETE /sessions/{id}/steps/last removes last step and reverts session | unit | `pytest tests/test_game.py::test_delete_last_step -x` | Wave 0 |
| SESSION-02 | DELETE /sessions/{id} hard-deletes archived session | unit | `pytest tests/test_game.py::test_delete_archived_session -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `cd backend && pytest tests/test_game.py -x -q`
- **Per wave merge:** `cd backend && pytest -x -q`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `backend/tests/test_cache.py` — covers CACHE-01, CACHE-02 (nightly job stubs)
- [ ] `backend/tests/test_game.py` — append test stubs for SESSION-01, SESSION-02 (delete endpoints)
- [ ] Install: `apscheduler>=3.10.4,<4.0` — not yet in `requirements.txt`
- [ ] Install: `@radix-ui/react-dialog` — not yet in `package.json`
- [ ] Create: `frontend/src/components/ui/dialog.tsx`

---

## Sources

### Primary (HIGH confidence)
- Direct codebase inspection:
  - `backend/app/main.py` — lifespan structure
  - `backend/app/routers/game.py` — all helper functions, schemas, router patterns
  - `backend/app/models/__init__.py` — ORM schema, nullable fields
  - `backend/app/services/tmdb.py` — TMDBClient, Semaphore, timeout settings
  - `backend/requirements.txt` — installed packages (no APScheduler; no apscheduler)
  - `frontend/src/lib/api.ts` — DTO types, all API methods
  - `frontend/src/App.tsx` — layout structure
  - `frontend/src/components/NavBar.tsx` — NavBar structure
  - `frontend/src/pages/GameSession.tsx` — radarrStatus at lines 410–422, view state, now-playing card
  - `frontend/src/pages/ArchivedSessions.tsx` — session list structure
  - `frontend/src/pages/GameLobby.tsx` — Watch History tab at line 303
  - `frontend/src/components/MovieFilterSidebar.tsx` — Collapsible sidebar structure
  - `frontend/src/components/MovieCard.tsx` — existing card fields
  - `frontend/src/components/ui/*.tsx` — confirms Dialog component absent
  - `frontend/package.json` — installed npm packages
  - `.planning/STATE.md` — architectural decisions, established patterns
  - `.planning/phases/04-caching-ui-ux-polish-and-session-management/04-CONTEXT.md` — locked decisions

### Secondary (MEDIUM confidence)
- APScheduler 3.x `AsyncIOScheduler` API pattern — consistent with widely documented FastAPI + APScheduler integration; version pinning recommendation based on known 3.x → 4.x breaking API change

### Tertiary (LOW confidence)
- None — no unverified WebSearch claims made

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all packages verified against requirements.txt / package.json; APScheduler is only new dependency, well-established
- Architecture: HIGH — patterns derived from reading existing production code, not speculation
- Pitfalls: HIGH — most pitfalls derive from documented STATE.md decisions and direct code inspection

**Research date:** 2026-03-17
**Valid until:** 2026-04-17 (stable stack; 30-day window)
