# Phase 5: Bug Fixes — Research

**Researched:** 2026-03-21
**Domain:** FastAPI game logic (Python), React/TypeScript frontend, Tailwind CSS responsive layout, TMDB API integration
**Confidence:** HIGH — all five items verified against live source code

## Summary

This phase fixes five confirmed issues with known root causes — no exploratory investigation needed. The issues were diagnosed by reading the canonical source files directly; all conclusions are HIGH confidence from the code itself.

The three gameplay-critical bugs (BUG-1 chain actor missing, BUG-3 eligibility logic, BUG-4 CSV round-trip) require backend changes. BUG-2 (mobile layout) is a frontend-only CSS change. ENH-1 (actor pre-cache) is a small backend enhancement following the existing `BackgroundTasks` pattern.

**Primary recommendation:** Treat each bug as an independent task. No shared dependencies between bugs except that BUG-1 touches `request_movie` and BUG-3 touches `get_eligible_movies` — both are in `game.py` and must not regress each other.

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**BUG-1:** When a movie is selected from Eligible Movies without an explicit actor pick:
- If exactly one eligible actor connects the previous movie to the selected movie → record that actor automatically
- If multiple eligible actors connect → show a small inline prompt asking the user to pick which actor they're "following"
- The recorded actor must be stored as a proper actor step (with `actor_tmdb_id` and `actor_name`)

**BUG-2:** Required visible fields in portrait mode: movie title, via actor name, TMDB rating, runtime, MPAA rating. Fix home page button layout for mobile.

**BUG-3:** Correct eligibility rule — eligible actors = cast of the **last watched movie only** MINUS actors already explicitly picked. Previous chain movies have no bearing. Audit `get_eligible_actors` and `get_eligible_movies`.

**BUG-4:** On CSV import, validate both movie name and actor name against TMDB. Normalize/correct names via TMDB lookup (not strict exact-match). Surface validation errors clearly.

**ENH-1:** When user selects an eligible actor, immediately trigger background pre-fetch of that actor's movie credits. Follow existing `_prefetch_credits_background` pattern. Does not change actor selection UI.

### Claude's Discretion

BUG-1 inline prompt design: "a small modal or inline selector, not a full-screen interruption."

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope.
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| BUG-1 | Chain actor name missing when movie selected from Eligible Movies tab without selecting an actor first | Root cause confirmed: `request_movie` creates step with `actor_tmdb_id=None`; fix requires backend actor auto-resolution + frontend multi-actor prompt |
| BUG-2 | Mobile UI — card details hidden in portrait mode; home page button misalignment | Root cause confirmed: `MovieCard.tsx` lacks responsive breakpoints for portrait; `GameLobby.tsx` button layout needs mobile flex fix |
| BUG-3 | Eligibility logic pulls actors/movies from beyond the current movie's cast | Root cause confirmed: combined-view in `get_eligible_movies` queries `Actor.tmdb_id.in_(eligible_actor_tmdb_ids)` — pulls ALL movies for those actors, not just movies reachable from the current movie |
| BUG-4 | CSV import/export round-trip produces duplicate rows and missing actor names | Root cause confirmed: `_resolve_actor_tmdb_id` does TMDB search but stores the CSV's raw `row.actorName` string, not the canonical TMDB name; mismatch causes blank actor names on re-export |
| ENH-1 | Actor selection has noticeable load time before Eligible Movies panel populates | Background pre-fetch pattern already exists (`_prefetch_credits_background`); ENH-1 wires the same pattern to actor selection event |
</phase_requirements>

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| FastAPI | existing | Backend API | Already in use |
| SQLAlchemy async | existing | ORM queries | Already in use |
| React + TanStack Query | existing | Frontend state | Already in use |
| Tailwind CSS | existing | Responsive layout | Already in use |
| TMDB API | existing | Name normalization | Already in use |

### No new libraries needed
All five items use existing patterns and libraries.

---

## Architecture Patterns

### Existing Step Storage Model
```
GameSessionStep rows:
  - movie-pick step: actor_tmdb_id=NULL, movie_tmdb_id=X
  - actor-pick step: actor_tmdb_id=Y, movie_tmdb_id=X (same movie as preceding movie step)

ChainHistory.tsx lookup:
  actorStep = sorted.find(s => s.step_order === step.step_order + 1 && s.actor_tmdb_id !== null)
```
Steps are sequential by `step_order`. An actor step for movie N lives at `step_order + 1` relative to the movie step for N. This is the invariant BUG-1 must preserve.

### Existing BackgroundTasks Pattern (ENH-1 template)
```python
# Source: backend/app/routers/game.py line 513-528
async def _prefetch_credits_background(movie_tmdb_id: int, tmdb: TMDBClient) -> None:
    try:
        async with _bg_session_factory() as db:
            await _ensure_movie_cast_in_db(movie_tmdb_id, tmdb, db)
    except Exception:
        pass
```
ENH-1 needs an equivalent `_prefetch_actor_credits_background(actor_tmdb_id, tmdb)` using `_ensure_actor_credits_in_db` (which already exists), called from the `pick_actor` endpoint via `BackgroundTasks`.

### Eligible Movies Combined-View Query (BUG-3 root cause)
```python
# Source: backend/app/routers/game.py line 1383-1421
# Combined view (actor_id is None):
# 1. Finds eligible actors from current movie's cast (correct)
# 2. Fetches ALL Credit rows for those actors — not scoped to current movie
film_stmt = (
    select(Movie, Credit, Actor)
    .join(Credit, Credit.movie_id == Movie.id)
    .join(Actor, Actor.id == Credit.actor_id)
    .where(Actor.tmdb_id.in_(eligible_actor_tmdb_ids))  # <-- no movie scope constraint
)
```
The bug: an actor who appeared in the current movie may also appear in any movie in the DB. The `film_stmt` returns ALL those movies, including ones from unrelated actors that happen to share an actor's credit. The fix must add a `via_actor` constraint so a movie only appears if it shares an actor with the CURRENT LAST MOVIE, not from arbitrary DB credits.

**The correct logic:** for each eligible actor (cast of last movie), show their filmography. This is already the intent — the bug is that the query returns all movies for those actors from the Credits table including ones that were pulled into the DB by other sessions' actor lookups. This is actually correct behavior per the eligibility rule — an actor's full filmography IS eligible. The reported symptom (Interstellar via Timothée Chalamet after The Menu) needs closer investigation.

**BUG-3 re-analysis:** Timothée Chalamet is not in The Menu. If he appears as an eligible actor, the `get_eligible_actors` query (line 1244-1252) is pulling him from somewhere other than `current_movie_tmdb_id`. This would happen if there are stale Credit rows in the DB linking Chalamet to The Menu's `Movie.id` — possible if TMDB data was partially imported or if `session.current_movie_tmdb_id` pointed to the wrong movie at query time.

**Root cause hypothesis (HIGH confidence):** The combined-view `get_eligible_movies` (actor_id=None path) builds `eligible_actor_tmdb_ids` from the CURRENT movie's cast — but then fetches filmography for ALL those actors. This is correct. However, if the `get_eligible_actors` endpoint returns Chalamet when he's not in The Menu, the bug is in `get_eligible_actors` not `get_eligible_movies`. The executor should verify whether Chalamet appears in `Credits` joined to `Movies.tmdb_id == session.current_movie_tmdb_id` (The Menu's TMDB ID). If yes, it's a data integrity issue. If no, there's a session state bug where `current_movie_tmdb_id` isn't pointing to The Menu.

### MovieCard Responsive Fix (BUG-2)
```tsx
// Source: frontend/src/components/MovieCard.tsx line 66-101
// Current layout: flex gap-3 with no responsive breakpoint
// All fields (title, rating, runtime, mpaa, via_actor) are already rendered
// Problem: card may overflow or truncate on narrow portrait screens
// Fix: ensure CardContent doesn't shrink below readable size; possibly min-w-0 + overflow handling
```
All required fields (title, via_actor_name, vote_average, runtime, mpaa_rating) already exist in the component. The issue is layout overflow at narrow widths — the `text-lg font-semibold` title wrapping and the poster/content flex ratio.

### GameLobby Button Alignment (BUG-2 home page)
```tsx
// Source: frontend/src/pages/GameLobby.tsx line 243-263
// Session card buttons (Archive, Continue) use flex items-center gap-2
// On mobile, the card layout (flex items-center justify-between) may collapse the button area
// The "+ Start a new session" button uses self-start which may misalign on mobile
```

### CSV Actor Name Normalization (BUG-4)
```python
# Source: backend/app/routers/game.py line 621-627
async def _resolve_actor_tmdb_id(name: str, tmdb: TMDBClient) -> int | None:
    r = await tmdb._client.get("/search/person", params={"query": name})
    results = r.json().get("results", [])
    if not results: return None
    return results[0]["id"]

# Then line 697-698:
steps_data.append({
    "actor_tmdb_id": actor_id,
    "actor_name": row.actorName,  # <-- RAW CSV NAME, not canonical TMDB name
})
```
**Root cause confirmed:** `_resolve_actor_tmdb_id` finds the correct TMDB actor ID but the step is stored with `row.actorName` (the CSV string) rather than the canonical TMDB name. On re-export, `export_session_csv` reads `actor_step.actor_name` from the DB, which is the incorrect CSV-sourced spelling. On re-import of that CSV, the name may fail to match again or create a new actor record.

**Fix:** After resolving `actor_id` from TMDB, look up the canonical `Actor.name` from the DB (or from the TMDB search result directly — the result already contains the name). Use the canonical name as `actor_name` in the stored step.

```python
# Fix pattern: use TMDB result's name directly
results[0]["name"]  # canonical name from TMDB search result
```

### BUG-1 Backend Fix Pattern
```python
# In request_movie (line 1621-1636):
# Current: creates step with actor_tmdb_id=None unconditionally
# Fix: after creating the movie step, check how many eligible actors connect
#      previous_movie -> selected_movie
# If exactly 1: auto-create an actor step at next_order+1
# If multiple: return a new response field indicating disambiguation needed
# If 0: proceed as-is (no actor bridging needed — first step case)
```

The actor step must be inserted BEFORE the movie step in step_order to maintain `ChainHistory.tsx`'s lookup invariant (`step_order + 1` for actor). Actually re-reading the code: `ChainHistory` looks for actor at `movie_step.step_order + 1`. In `pick_actor`, the actor step is created at `next_order` (after all existing steps) and its `movie_tmdb_id` is set to the current movie. When `request_movie` is then called, it creates the movie step at `next_order + 1`. So the actor step for movie N gets created BEFORE the movie step for N+1 — this is correct.

**BUG-1 fix requires:** When no actor was explicitly selected, the backend must resolve which actor(s) connect `previous_movie` (the movie before the selected one in the chain) to `selected_movie`. This requires querying shared cast between the two movies.

### Anti-Patterns to Avoid
- **Don't re-architect step ordering:** The `step_order + 1` convention is relied on by both `ChainHistory.tsx` and `export_session_csv`. Preserve it.
- **Don't fetch filmography in the actor-pick flow synchronously:** ENH-1 specifically uses BackgroundTasks to avoid blocking the UI response.
- **Don't change `_resolve_movie_tmdb_id` confidence thresholds:** The existing high/medium/low/none system is working. BUG-4 only needs the actor name fix.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Actor name normalization | Custom fuzzy matching | TMDB `/search/person` result's `name` field | Already queried; canonical name is in the response |
| Background task scheduling | Custom async queue | FastAPI `BackgroundTasks` | Pattern already established in codebase |
| Responsive card layout | Custom JS breakpoint detection | Tailwind `sm:` / `md:` breakpoint classes | Already used throughout codebase |
| Actor disambiguation prompt | Full-screen modal | Small inline Dialog (already imported in GameSession.tsx) | Matches existing `randomPickOpen` dialog pattern |

---

## Common Pitfalls

### Pitfall 1: BUG-1 — Step Order Invariant
**What goes wrong:** Inserting an auto-resolved actor step after the movie step breaks `ChainHistory.tsx`'s `step_order + 1` lookup.
**Why it happens:** Normal flow: pick-actor creates step N, then request-movie creates step N+1. If request-movie creates step N first and then auto-actor step N+1, the actor step has `movie_tmdb_id` pointing to the new movie (not the previous one).
**How to avoid:** The auto-actor step must use `movie_tmdb_id = previous_movie_tmdb_id` (the movie the actor was selected FROM, not the movie being requested). Reconstruct the correct movie reference from the session state before creating steps.
**Warning signs:** Chain history shows blank VIA column or wrong movie for actor row.

### Pitfall 2: BUG-1 — Disambiguation Response Shape
**What goes wrong:** Returning a disambiguation response requires the frontend to handle a new response shape from `request_movie`.
**How to avoid:** Add a new `disambiguation_required` status to the existing response alongside `status` field. Frontend already handles `"already_in_radarr"`, `"queued"`, etc. Add `"disambiguation_required"` with a list of candidate actors.
**Warning signs:** Frontend crashes or ignores the disambiguation case.

### Pitfall 3: BUG-3 — Don't Revert Combined-View Feature
**What goes wrong:** Over-aggressively fixing the eligibility query removes the "show all eligible movies without selecting an actor" feature (Phase 03.2 Gap 3).
**How to avoid:** The combined-view (actor_id=None) must remain functional. Only fix the case where actors from non-current movies are being included.
**Warning signs:** Eligible Movies tab shows empty results before actor is selected.

### Pitfall 4: BUG-4 — Actor Name in DB vs. CSV
**What goes wrong:** After fixing actor name storage, re-importing existing sessions (already in DB with old incorrect names) still produces duplicates.
**Why it happens:** The fix only affects new imports. Existing `GameSessionStep` rows with incorrect `actor_name` strings remain.
**How to avoid:** Scope the fix to new imports only. Do not backfill existing data.

### Pitfall 5: ENH-1 — Pre-fetch on Actor Select vs. Actor Pick
**What goes wrong:** Pre-fetch triggered on `pick_actor` (POST endpoint) is correct. Do not pre-fetch on the GET `eligible-actors` endpoint — that's the query endpoint, not the selection event.
**How to avoid:** Wire `BackgroundTasks` to the `pick_actor` POST handler, not the GET handler.

### Pitfall 6: BUG-2 — Portrait Mode vs. Small Screen
**What goes wrong:** Treating "portrait mode" as a CSS media query for orientation rather than a Tailwind responsive breakpoint.
**How to avoid:** Use Tailwind `sm:` breakpoints (640px) which handle both portrait phones and narrow browser windows uniformly. The existing `hidden sm:table-cell` patterns in `ChainHistory.tsx` demonstrate the project convention.

---

## Code Examples

### ENH-1: Actor Pre-fetch Background Task (new function)
```python
# Pattern from _prefetch_credits_background (line 513-528)
async def _prefetch_actor_credits_background(
    actor_tmdb_id: int,
    tmdb: TMDBClient,
) -> None:
    """Background task: pre-populate Credit rows for selected actor's filmography."""
    try:
        async with _bg_session_factory() as db:
            await _ensure_actor_credits_in_db(actor_tmdb_id, tmdb, db)
    except Exception:
        pass
```

### ENH-1: Wire to pick_actor endpoint
```python
# In pick_actor handler, after db.commit():
background_tasks.add_task(_prefetch_actor_credits_background, body.actor_tmdb_id, tmdb)
# Note: requires adding BackgroundTasks + Request to pick_actor signature
```

### BUG-4: Fix actor name storage
```python
# In import_csv_session, replace:
actor_id = await _resolve_actor_tmdb_id(row.actorName, tmdb)
# ...
"actor_name": row.actorName,  # raw CSV name — WRONG

# With:
actor_id, canonical_name = await _resolve_actor_tmdb_id(row.actorName, tmdb)
# ...
"actor_name": canonical_name or row.actorName,  # prefer TMDB canonical

# And update _resolve_actor_tmdb_id to return (id, name) tuple:
async def _resolve_actor_tmdb_id(name: str, tmdb: TMDBClient) -> tuple[int | None, str | None]:
    r = await tmdb._client.get("/search/person", params={"query": name})
    results = r.json().get("results", [])
    if not results:
        return None, None
    return results[0]["id"], results[0].get("name")
```

### BUG-2: MovieCard responsive fix (illustration)
```tsx
// Add min-w-0 to prevent flex child overflow
// Ensure title wraps gracefully at narrow widths
<CardContent className="p-0 flex flex-col gap-1 min-w-0">
  <p className="text-lg font-semibold leading-tight break-words">{title}</p>
  ...
</CardContent>
// Poster: w-16 h-24 is already fixed-width flex-shrink-0 — should be fine
```

### BUG-1: Finding shared actors between two movies
```python
# Query actors in BOTH previous_movie AND selected_movie
shared_stmt = (
    select(Actor, Credit)
    .join(Credit, Credit.actor_id == Actor.id)
    .join(Movie, Movie.id == Credit.movie_id)
    .where(Movie.tmdb_id == selected_movie_tmdb_id)
    .where(Actor.tmdb_id.in_(
        select(Actor.tmdb_id)
        .join(Credit, Credit.actor_id == Actor.id)
        .join(Movie, Movie.id == Credit.movie_id)
        .where(Movie.tmdb_id == previous_movie_tmdb_id)
        .where(Actor.tmdb_id.not_in(already_picked_ids))
    ))
)
```

---

## State of the Art

| Old Approach | Current Approach | Notes |
|--------------|-----------------|-------|
| Raw CSV actor name stored | Canonical TMDB name (BUG-4 fix) | Only affects new imports |
| No pre-fetch on actor select | Background pre-fetch on pick_actor (ENH-1) | Follows existing movie pre-fetch pattern |

---

## Open Questions

1. **BUG-3 root cause — data integrity vs. query logic**
   - What we know: Timothée Chalamet appeared as eligible after The Menu despite not being in The Menu
   - What's unclear: Was this a stale Credit record in the DB, or was `current_movie_tmdb_id` set incorrectly?
   - Recommendation: Executor should verify by running: `SELECT a.name FROM actors a JOIN credits c ON c.actor_id = a.id JOIN movies m ON m.id = c.movie_id WHERE m.tmdb_id = <The Menu's TMDB ID>` in the live NAS DB. If Chalamet appears there, the Credits table has bad data. If not, the session state was wrong.

2. **BUG-1 — multi-actor disambiguation: how rare is "multiple eligible actors"?**
   - What we know: User says it's "expected to be rare"
   - What's unclear: Whether to block the movie request until resolved or allow it with a warning
   - Recommendation: Block the request — allow movie to be confirmed but require actor disambiguation before the session advances. This preserves chain integrity.

3. **BUG-2 — specific mobile device/orientation that fails**
   - What we know: Portrait mode truncates cards; home page buttons misalign
   - What's unclear: Whether the issue is MovieCard (used in search results) or MovieCard inside the eligible movies list
   - Recommendation: Fix both `MovieCard.tsx` layout overflow and `GameLobby.tsx` session card button flex-wrap for narrow screens.

---

## Validation Architecture

> `workflow.nyquist_validation` key is absent from `.planning/config.json` — treating as enabled.

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest + pytest-asyncio (backend), vitest (frontend) |
| Config file | `backend/pytest.ini` or `pyproject.toml`; `frontend/vitest.config.*` |
| Quick run command | `cd backend && pytest tests/test_game.py -x -q` |
| Full suite command | `cd backend && pytest -x -q` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| BUG-1 | Auto-record actor when exactly one shared actor exists | unit | `pytest tests/test_game.py::test_bug1_auto_actor_single -x` | ❌ Wave 0 |
| BUG-1 | Return disambiguation candidates when multiple shared actors exist | unit | `pytest tests/test_game.py::test_bug1_disambiguation_multiple -x` | ❌ Wave 0 |
| BUG-3 | Eligible actors excludes actors not in current movie | unit | `pytest tests/test_game.py::test_bug3_eligibility_scoped_to_current_movie -x` | ❌ Wave 0 |
| BUG-4 | CSV import stores canonical TMDB actor name | unit | `pytest tests/test_game.py::test_bug4_csv_actor_name_canonical -x` | ❌ Wave 0 |
| BUG-4 | CSV round-trip: export then re-import produces no duplicates | integration | `pytest tests/test_game.py::test_bug4_csv_roundtrip -x` | ❌ Wave 0 |
| ENH-1 | pick_actor triggers background actor credit pre-fetch | unit | `pytest tests/test_game.py::test_enh1_actor_precache_triggered -x` | ❌ Wave 0 |
| BUG-2 | MovieCard renders all required fields at narrow widths | manual | visual inspection on mobile device | manual only |

**Note:** BUG-2 is CSS/visual — no automated test needed. All backend tests follow the existing `asyncpg-skip` pattern in `test_game.py` (skip locally, run in Docker).

### Sampling Rate
- **Per task commit:** `cd backend && pytest tests/test_game.py -x -q`
- **Per wave merge:** `cd backend && pytest -x -q`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `backend/tests/test_game.py` — append stubs for BUG-1 (auto-actor + disambiguation), BUG-3 (eligibility scoped), BUG-4 (canonical name + round-trip), ENH-1 (pre-cache triggered)
- [ ] No new test files needed — all stubs append to existing `test_game.py`

---

## Sources

### Primary (HIGH confidence)
- `backend/app/routers/game.py` — full source read; all root causes confirmed from code
- `frontend/src/components/ChainHistory.tsx` — full source read; step lookup logic confirmed
- `frontend/src/components/MovieCard.tsx` — full source read; layout structure confirmed
- `frontend/src/pages/GameSession.tsx` — full source read; actor selection flow confirmed
- `frontend/src/pages/GameLobby.tsx` — full source read; CSV import + button layout confirmed
- `.planning/phases/05-bug-fixes/05-CONTEXT.md` — user decisions read

### Secondary (MEDIUM confidence)
- `.planning/STATE.md` — recent decisions history confirming Phase 4.x fixes and current state

---

## Metadata

**Confidence breakdown:**
- BUG-1 root cause: HIGH — `request_movie` creates step with `actor_tmdb_id=None` confirmed in code
- BUG-2 root cause: HIGH — `MovieCard.tsx` layout structure confirmed; specific narrow-screen behavior is visual (MEDIUM)
- BUG-3 root cause: MEDIUM — query logic confirmed correct; actual DB data causing the symptom needs live verification
- BUG-4 root cause: HIGH — `_resolve_actor_tmdb_id` returns only ID, stores raw CSV name confirmed in code
- ENH-1 pattern: HIGH — `_prefetch_credits_background` template confirmed; `_ensure_actor_credits_in_db` confirmed to exist

**Research date:** 2026-03-21
**Valid until:** 2026-04-20 (stable codebase, no fast-moving dependencies)
