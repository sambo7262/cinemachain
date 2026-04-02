# Phase 11: Session Enhancements — Research

**Researched:** 2026-03-31
**Domain:** FastAPI (SQLAlchemy async) + React/TanStack Query — in-session state persistence with new DB tables and API endpoints
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**D-01: Feature distinction — Save vs Shortlist**
Two separate features with different scopes and lifecycles:
- Save: session-wide bookmark; persists until movie is picked or manually toggled off; auto-removed when the saved movie is added to the chain
- Shortlist: per-step finalist tray; auto-clears when `request_movie` is called; resets for every new movie-selection step

**D-02: Persistence — backend storage (not localStorage)**
Both Save and Shortlist survive page refresh and work across devices. Requires two new DB tables:
- `SessionSave`: `session_id (FK)`, `tmdb_id`, `saved_at` + UniqueConstraint
- `SessionShortlist`: `session_id (FK)`, `tmdb_id` + UniqueConstraint

**API surface (all new endpoints):**
- `POST /sessions/{id}/saves/{tmdb_id}`
- `DELETE /sessions/{id}/saves/{tmdb_id}`
- `GET /sessions/{id}/saves`
- `POST /sessions/{id}/shortlist/{tmdb_id}`
- `DELETE /sessions/{id}/shortlist/{tmdb_id}`
- `DELETE /sessions/{id}/shortlist` (clear all)
- `GET /sessions/{id}/shortlist`
- Existing `POST /sessions/{id}/request_movie` gains side effects: clear shortlist + delete save for the picked tmdb_id

**D-03: Save affordance**
- Movie row: `Star` icon overlaid on poster thumbnail — outline = unsaved, filled gold = saved
- Row treatment: `bg-amber-500/10` warm tint on the `<tr>` when saved
- Splash dialog: small `Star` icon toggle in header area (no full button)

**D-04: Shortlist affordance**
- Movie row: `ListCheck` or `CheckSquare` icon — outline = not shortlisted, filled/active = shortlisted; positioned separately from save star
- Filter: "Shortlist" toggle button in filter area; when active shows only shortlisted movies
- Clear All button: appears when shortlist has items; calls `DELETE /sessions/{id}/shortlist`
- Shortlisted rows: `bg-blue-500/10` tint

**D-05: Filter stacking**
Both "Saved" and "Shortlist" filters are client-side toggles that stack with all existing filters (genre, MPAA, runtime, unwatched-only, search). All active filters must be satisfied simultaneously. Add "Saved ★" and "Shortlist ✓" toggle buttons to the filter bar matching existing toggle button style.

**D-06: Shortlist lifecycle — auto-clear on movie selection**
- Backend: `request_movie` handler clears `SessionShortlist` rows for session before/at commit
- Frontend: `queryClient.invalidateQueries(["shortlist", sid])` after `requestMovie` resolves

**D-07: Saved movie when picked**
`request_movie` handler also deletes `SessionSave` row for the picked `tmdb_id` as a side effect.

**D-08: Gold/blue row treatment**
Saved movies: `bg-amber-500/10`; shortlisted movies: `bg-blue-500/10`; both simultaneously active = Claude's discretion (combined treatment acceptable).

### Claude's Discretion
- How to combine `bg-amber-500/10` + `bg-blue-500/10` when a movie is both saved and shortlisted simultaneously (e.g., a combined `bg-amber-500/10` + `bg-blue-500/10` class sequence, or a distinct third color)
- Exact position of `Star` and `ListCheck` icons in the poster overlay cell
- Whether `saved` and `shortlisted` booleans are embedded in `EligibleMovieResponse` (join on eligible-movies query) or fetched separately via the GET endpoints and merged client-side

### Deferred Ideas (OUT OF SCOPE)
None explicitly deferred in CONTEXT.md.
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| SESS-01 | User can tag/save any movie in the eligible movies list during an active session | D-03 icon pattern; Star from lucide-react (already in imports); `POST /saves/{tmdb_id}` endpoint; `useMutation` pattern established in codebase |
| SESS-02 | Saved movies persist for the duration of the session (survive tab changes, page refreshes, device changes) | D-02 backend DB storage; `GET /saves` hydration on mount via `useQuery`; two-table model confirmed sufficient |
| SESS-03 | Eligible movies list can be filtered to show only saved movies | D-05 client-side filter stacking; extend `filteredMovies` chain in `GameSession.tsx`; new toggle button matching existing "All Movies / Unwatched Only" style |
| SESS-04 | User can shortlist 2–6 eligible movies; list filters to shortlisted items for comparison | D-04 `ListCheck`/`CheckSquare` icon; `POST/DELETE /shortlist/{tmdb_id}`; shortlist filter toggle + Clear All button; D-06 auto-clear in `request_movie` |
</phase_requirements>

---

## Summary

Phase 11 adds two in-session decision-making tools — Save (session-scoped bookmark) and Shortlist (step-scoped finalist tray) — to Game Mode's eligible movies list. Both features require backend persistence via two new SQLAlchemy models (`SessionSave`, `SessionShortlist`), a new Alembic migration, seven new API endpoints in `game.py`, and frontend integration in `GameSession.tsx` using TanStack Query mutations.

The existing codebase provides a strong foundation: `useMutation` is already used throughout `GameSession.tsx`, `queryClient.invalidateQueries` is a known pattern, `EligibleMovieResponse` can be extended with `saved`/`shortlisted` booleans, and `filteredMovies` is a simple client-side `.filter()` chain that's easy to extend. The `request_movie` endpoint already commits in a single `await db.commit()` block — the shortlist/save cleanup can be added as DB deletes before that commit.

The main complexity is the dual-state visual treatment (a movie can be both saved and shortlisted simultaneously) and keeping the TanStack Query cache consistent between the eager `GET /saves` + `GET /shortlist` fetches and the mutations that modify state. The recommended approach is to embed `saved` and `shortlisted` booleans directly in `EligibleMovieResponse` (via LEFT JOIN in the eligible-movies query) rather than fetching them separately — this simplifies cache coherence and reduces waterfall requests.

**Primary recommendation:** Extend `EligibleMovieResponse` with `saved: bool` and `shortlisted: bool`, computed via subquery/join in `get_eligible_movies`. Mutations call `POST/DELETE` endpoints and then invalidate the `eligibleMovies` query to trigger re-fetch with fresh flag state.

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| SQLAlchemy async | 2.x (already in project) | New model tables + query joins | Established pattern; all existing models use `Mapped[]` + `mapped_column` |
| Alembic | (already in project) | DB migration for new tables | All schema changes go through Alembic — migration 0010 |
| FastAPI | (already in project) | 7 new route handlers in `game.py` | Existing router; no new dependencies |
| TanStack Query v5 | (already in project) | `useQuery` for saves/shortlist; `useMutation` for toggle actions | `useMutation` + `queryClient.invalidateQueries` already used throughout |
| lucide-react | (already in project) | `Star`, `ListCheck`/`CheckSquare`, `Trash2` icons | Already imported in `GameSession.tsx`; `Star` is already imported |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| shadcn/ui `Button` | (already in project) | "Saved ★" and "Shortlist ✓" filter toggle buttons | Match existing "All Movies / Unwatched Only" toggle style |
| Tailwind `cn()` | (already in project) | Conditional row background classes | Already used for `<tr>` class composition in movie table |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Embedding `saved`/`shortlisted` in `EligibleMovieResponse` | Separate `GET /saves` + `GET /shortlist` fetches merged client-side | Separate fetches create waterfall + three-way cache sync complexity; embedding in eligible-movies response is simpler and already returns per-movie data |
| `bg-amber-500/10` + `bg-blue-500/10` on `<tr>` | CSS gradient or single merged color | Tailwind utility classes are direct and match existing approach; combined state can just apply both classes — browser renders additive alpha |

**Installation:** No new packages required — all dependencies already installed.

---

## Architecture Patterns

### Recommended Project Structure

New files:
```
backend/alembic/versions/20260331_0010_session_saves_shortlist.py
```

Modified files:
```
backend/app/models/__init__.py         # SessionSave, SessionShortlist models
backend/app/routers/game.py            # EligibleMovieResponse + 7 new endpoints + request_movie side-effects
frontend/src/lib/api.ts                # EligibleMovieDTO extensions + 7 new api.* functions
frontend/src/pages/GameSession.tsx     # Save/shortlist state, mutations, filter toggles, row rendering
frontend/src/components/MovieFilterSidebar.tsx  # FilterState extension (or new toggle buttons outside sidebar)
backend/tests/test_game.py             # New asyncpg-skip tests for save/shortlist endpoints
```

### Pattern 1: Backend model addition (established pattern)

New models follow the exact same `Mapped[]` + `mapped_column` pattern as existing models. Both tables use `ondelete="CASCADE"` so session deletion auto-cleans rows.

```python
# Source: existing models/__init__.py pattern (verified by code read)
class SessionSave(Base):
    __tablename__ = "session_saves"
    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("game_sessions.id", ondelete="CASCADE"))
    tmdb_id: Mapped[int] = mapped_column()
    saved_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    __table_args__ = (UniqueConstraint("session_id", "tmdb_id"),)

class SessionShortlist(Base):
    __tablename__ = "session_shortlist"
    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("game_sessions.id", ondelete="CASCADE"))
    tmdb_id: Mapped[int] = mapped_column()
    __table_args__ = (UniqueConstraint("session_id", "tmdb_id"),)
```

### Pattern 2: Alembic migration (established pattern)

```python
# Source: 20260322_0008_rt_scores.py and 20260331_0009_actor_filmography_fetched.py — verified
revision: str = "0010"
down_revision: Union[str, None] = "0009"

def upgrade() -> None:
    op.create_table(
        "session_saves",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("session_id", sa.Integer(), sa.ForeignKey("game_sessions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("tmdb_id", sa.Integer(), nullable=False),
        sa.Column("saved_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("session_id", "tmdb_id"),
    )
    op.create_table(
        "session_shortlist",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("session_id", sa.Integer(), sa.ForeignKey("game_sessions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("tmdb_id", sa.Integer(), nullable=False),
        sa.UniqueConstraint("session_id", "tmdb_id"),
    )

def downgrade() -> None:
    op.drop_table("session_shortlist")
    op.drop_table("session_saves")
```

### Pattern 3: Extending EligibleMovieResponse with saved/shortlisted flags

Add `saved: bool = False` and `shortlisted: bool = False` to `EligibleMovieResponse`. In `get_eligible_movies`, after building `movies_map`, execute two scalar queries to get the saved and shortlisted tmdb_id sets for the session, then set flags when building the response list.

```python
# Source: established pattern — get_eligible_movies already builds movies_map dict, then iterates
saved_result = await db.execute(
    select(SessionSave.tmdb_id).where(SessionSave.session_id == session_id)
)
saved_set = {row[0] for row in saved_result.all()}

shortlist_result = await db.execute(
    select(SessionShortlist.tmdb_id).where(SessionShortlist.session_id == session_id)
)
shortlist_set = {row[0] for row in shortlist_result.all()}

# Then in list comprehension building response items:
# "saved": item["tmdb_id"] in saved_set,
# "shortlisted": item["tmdb_id"] in shortlist_set,
```

### Pattern 4: New route handlers (upsert pattern for adds, delete for removes)

Use PostgreSQL's `INSERT ... ON CONFLICT DO NOTHING` (via `pg_insert` — already imported as `from sqlalchemy.dialects.postgresql import insert as pg_insert`) for save/shortlist adds. This avoids 409 on double-tap.

```python
# Source: pg_insert already imported in game.py — verified by code read
@router.post("/sessions/{session_id}/saves/{tmdb_id}", status_code=204)
async def save_movie(session_id: int, tmdb_id: int, db: AsyncSession = Depends(get_db)):
    stmt = pg_insert(SessionSave).values(
        session_id=session_id, tmdb_id=tmdb_id, saved_at=datetime.utcnow()
    ).on_conflict_do_nothing()
    await db.execute(stmt)
    await db.commit()

@router.delete("/sessions/{session_id}/saves/{tmdb_id}", status_code=204)
async def unsave_movie(session_id: int, tmdb_id: int, db: AsyncSession = Depends(get_db)):
    await db.execute(
        sa.delete(SessionSave).where(
            SessionSave.session_id == session_id,
            SessionSave.tmdb_id == tmdb_id
        )
    )
    await db.commit()
```

### Pattern 5: Frontend mutation + cache invalidation (established pattern)

```typescript
// Source: existing GameSession.tsx useMutation patterns — verified by code read
const saveMovieMutation = useMutation({
  mutationFn: (tmdbId: number) => api.saveMovie(sid, tmdbId),
  onSuccess: () => queryClient.invalidateQueries({ queryKey: ["eligibleMovies", sid] }),
})

const unsaveMovieMutation = useMutation({
  mutationFn: (tmdbId: number) => api.unsaveMovie(sid, tmdbId),
  onSuccess: () => queryClient.invalidateQueries({ queryKey: ["eligibleMovies", sid] }),
})
```

Invalidating `eligibleMovies` re-fetches the whole list with fresh `saved`/`shortlisted` booleans. This is simpler than maintaining a separate saves/shortlist query.

### Pattern 6: Client-side filter extension (established pattern)

```typescript
// Source: existing filteredMovies chain in GameSession.tsx — verified by code read
// Current:
const filteredMovies = allEligibleMovies
  .filter(genre)
  .filter(mpaa)
  .filter(runtime)

// Extended (add two more .filter() calls):
  .filter((m) => !showSavedOnly || m.saved)
  .filter((m) => !showShortlistOnly || m.shortlisted)
```

`showSavedOnly` and `showShortlistOnly` are new `useState<boolean>` in `GameSession.tsx`. They do NOT need to go into `FilterState` / `MovieFilterSidebar` — they live as top-level state in `GameSession.tsx` alongside `allMovies`, keeping the sidebar concern-separated.

### Pattern 7: request_movie side-effects (extend before commit)

```python
# Source: request_movie in game.py lines 1915–1920 — verified by code read
# BEFORE await db.commit() — add:
await db.execute(
    sa.delete(SessionShortlist).where(SessionShortlist.session_id == session_id)
)
await db.execute(
    sa.delete(SessionSave).where(
        SessionSave.session_id == session_id,
        SessionSave.tmdb_id == body.movie_tmdb_id
    )
)
# existing:
await db.commit()
```

### Anti-Patterns to Avoid

- **Separate saves/shortlist useQuery waterfall:** Fetching `GET /saves` and `GET /shortlist` independently from `GET /eligible-movies` creates a three-way loading state and complex merge logic. Embed flags in `EligibleMovieResponse` instead.
- **localStorage for persistence:** Explicitly ruled out by D-02 — cross-device requirement makes this impossible.
- **Clearing shortlist in frontend-only on movie confirm:** The backend must be the source of truth. Frontend invalidation alone would leave stale shortlist data if the user reloads mid-session.
- **Using `INSERT ... ON CONFLICT` without `pg_insert`:** Plain `db.add()` will raise `IntegrityError` on double-tap (UniqueConstraint). Use `pg_insert(...).on_conflict_do_nothing()` — the dialect import is already present in `game.py`.
- **Putting Saved/Shortlist toggles inside `MovieFilterSidebar`:** Would require passing `sid`, mutation functions, and session state into a sidebar that currently has no async dependencies. Keep toggle buttons in `GameSession.tsx`'s filter bar row.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Idempotent upsert for saves/shortlist | Custom check-then-insert logic | `pg_insert(...).on_conflict_do_nothing()` | Already imported in game.py; handles race condition and double-tap atomically |
| Icon toggle state | Custom icon components | lucide-react `Star` (fill prop) + `ListCheck` | Already installed; `Star` already imported in GameSession.tsx |
| Filter toggle UI | Custom checkbox or dropdown | shadcn `Button` with variant toggling | Matches existing "All Movies / Unwatched Only" toggle pattern exactly |

---

## Common Pitfalls

### Pitfall 1: `saved`/`shortlisted` flags go stale after mutation
**What goes wrong:** User clicks save star — mutation fires — but `EligibleMovieResponse` still shows `saved: false` because `eligibleMovies` query hasn't refetched.
**Why it happens:** TanStack Query uses stale-while-revalidate; invalidating must be done explicitly.
**How to avoid:** All save/unsave/shortlist/unshortlist mutations call `queryClient.invalidateQueries({ queryKey: ["eligibleMovies", sid] })` in their `onSuccess` callback.
**Warning signs:** Icon state doesn't update immediately after click.

### Pitfall 2: `pg_insert` not imported in models module
**What goes wrong:** `pg_insert` is imported in `game.py` (`from sqlalchemy.dialects.postgresql import insert as pg_insert`), not in `models/__init__.py`. New save/shortlist endpoint handlers in `game.py` can use it directly.
**Why it happens:** Developers assume the import must be added — it's already there.
**How to avoid:** Verify import at top of `game.py` before adding new handlers (confirmed present — line verified by code read).

### Pitfall 3: `filteredMovies` length check drives "Random" button state
**What goes wrong:** After adding saved/shortlist filters, the `filteredMovies.length === 0` guard on the Random button becomes more easily triggered, confusing users who have saved movies.
**Why it happens:** Random pick uses `filteredMovies` (correct behavior), but empty state with active Saved filter shows a generic "no movies" message.
**How to avoid:** Update the empty-state message to mention active filter context (e.g., "No saved movies. Clear the Saved filter to see all eligible movies.").

### Pitfall 4: Shortlist count exceeds 6 if client-side guard is skipped
**What goes wrong:** CONTEXT.md says shortlist should support 2–6 movies for comparison. The backend has no count enforcement — it will accept unlimited shortlist adds.
**Why it happens:** Backend endpoints are designed as simple upsert/delete; enforcement is UI responsibility.
**How to avoid:** Frontend disables the shortlist toggle icon when `shortlistedCount >= 6` and the movie is not already shortlisted. Backend needs no change — simpler to guard in UI. (Note: CONTEXT.md says "2–6 or 1" — the minimum is not enforced; only maximum of 6 needs a guard.)

### Pitfall 5: Alembic migration order — revision chain must stay linear
**What goes wrong:** New migration references wrong `down_revision`, breaking `alembic upgrade head`.
**Why it happens:** Copy-paste from older migration file.
**How to avoid:** `down_revision = "0009"` (the actor_filmography_fetched migration) — verified as current head.

### Pitfall 6: Both saved + shortlisted Tailwind classes on same `<tr>`
**What goes wrong:** Tailwind purges one or both classes if only applied conditionally at runtime in a `cn()` expression with dynamic strings.
**Why it happens:** Tailwind's JIT purge scans for complete class strings at build time.
**How to avoid:** Use literal class strings in `cn()` conditionals: `movie.saved && "bg-amber-500/10"`, `movie.shortlisted && "bg-blue-500/10"` — never build class strings dynamically (e.g., `bg-${color}-500/10`).

---

## Code Examples

### Save toggle on movie row (poster cell overlay)

```tsx
// Source: GameSession.tsx movie table row rendering pattern — verified by code read
// The poster cell (first <td>) already renders a 48x72px img with rounded corners.
// Overlay the Star icon absolutely-positioned on the poster:
<td className="px-4 py-2 relative">
  {movie.poster_path ? (
    <div className="relative w-12 h-[4.5rem]">
      <img src={...} className="w-12 h-[4.5rem] rounded object-cover" />
      <button
        className="absolute bottom-0.5 left-0.5 p-0.5 rounded bg-black/40 hover:bg-black/60"
        onClick={(e) => { e.stopPropagation(); toggleSave(movie) }}
      >
        <Star className={cn("w-3.5 h-3.5", movie.saved ? "fill-amber-400 text-amber-400" : "text-white")} />
      </button>
      <button
        className="absolute bottom-0.5 right-0.5 p-0.5 rounded bg-black/40 hover:bg-black/60"
        onClick={(e) => { e.stopPropagation(); toggleShortlist(movie) }}
      >
        <ListCheck className={cn("w-3.5 h-3.5", movie.shortlisted ? "fill-blue-400 text-blue-400" : "text-white")} />
      </button>
    </div>
  ) : (
    <div className="relative w-12 h-[4.5rem] rounded bg-muted">
      {/* same button overlays */}
    </div>
  )}
</td>
```

### Row background for saved + shortlisted states

```tsx
// Source: existing <tr> cn() pattern in GameSession.tsx — verified by code read
<tr
  key={movie.tmdb_id}
  onClick={movie.selectable ? () => handleMovieConfirm(movie) : undefined}
  className={cn(
    "transition-colors",
    movie.selectable ? "cursor-pointer hover:bg-accent/50" : "opacity-40 cursor-not-allowed",
    movie.saved && "bg-amber-500/10",
    movie.shortlisted && "bg-blue-500/10",
  )}
>
```

### Filter bar toggle buttons

```tsx
// Source: existing "All Movies / Unwatched Only" Button toggle in GameSession.tsx — verified by code read
<Button
  variant={showSavedOnly ? "default" : "outline"}
  size="sm"
  onClick={() => setShowSavedOnly((v) => !v)}
>
  Saved ★
</Button>
<Button
  variant={showShortlistOnly ? "default" : "outline"}
  size="sm"
  onClick={() => setShowShortlistOnly((v) => !v)}
>
  Shortlist ✓
</Button>
{shortlistedCount > 0 && (
  <Button variant="ghost" size="sm" onClick={() => clearShortlistMutation.mutate()}>
    <Trash2 className="w-3.5 h-3.5 mr-1" />
    Clear
  </Button>
)}
```

### api.ts new functions

```typescript
// Source: existing api object pattern in api.ts — verified by code read
saveMovie: (sessionId: number, tmdbId: number) =>
  apiFetch<void>(`/game/sessions/${sessionId}/saves/${tmdbId}`, { method: "POST" }),

unsaveMovie: (sessionId: number, tmdbId: number) =>
  apiFetch<void>(`/game/sessions/${sessionId}/saves/${tmdbId}`, { method: "DELETE" }),

addToShortlist: (sessionId: number, tmdbId: number) =>
  apiFetch<void>(`/game/sessions/${sessionId}/shortlist/${tmdbId}`, { method: "POST" }),

removeFromShortlist: (sessionId: number, tmdbId: number) =>
  apiFetch<void>(`/game/sessions/${sessionId}/shortlist/${tmdbId}`, { method: "DELETE" }),

clearShortlist: (sessionId: number) =>
  apiFetch<void>(`/game/sessions/${sessionId}/shortlist`, { method: "DELETE" }),
```

Note: `GET /saves` and `GET /shortlist` are only needed if saves/shortlist are NOT embedded in `EligibleMovieResponse`. With the recommended approach (embed booleans), these GET endpoints can be omitted from the frontend (but may still be useful for the backend to expose for completeness/future use).

---

## Validation Architecture

`workflow.nyquist_validation` key absent from config.json — treating as enabled.

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest + httpx AsyncClient |
| Config file | `backend/pytest.ini` (or pyproject.toml — check project root) |
| Quick run command | `cd backend && pytest tests/test_game.py -x -q` |
| Full suite command | `cd backend && pytest tests/ -x -q` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| SESS-01 | `POST /game/sessions/{id}/saves/{tmdb_id}` returns 204 | integration (asyncpg-skip) | `pytest tests/test_game.py::test_save_movie -x` | ❌ Wave 0 |
| SESS-01 | `DELETE /game/sessions/{id}/saves/{tmdb_id}` returns 204 | integration (asyncpg-skip) | `pytest tests/test_game.py::test_unsave_movie -x` | ❌ Wave 0 |
| SESS-01 | `POST /saves/{tmdb_id}` is idempotent (second call is 204 not 409) | integration (asyncpg-skip) | `pytest tests/test_game.py::test_save_movie_idempotent -x` | ❌ Wave 0 |
| SESS-02 | `GET /eligible-movies` response items include `saved: true` for previously saved tmdb_id | integration (asyncpg-skip) | `pytest tests/test_game.py::test_eligible_movies_saved_flag -x` | ❌ Wave 0 |
| SESS-03 | `EligibleMovieResponse` schema includes `saved` and `shortlisted` boolean fields | unit (schema validation) | `pytest tests/test_game.py::test_eligible_movie_response_schema -x` | ❌ Wave 0 |
| SESS-04 | `POST /shortlist/{tmdb_id}` returns 204; `GET /eligible-movies` shows `shortlisted: true` | integration (asyncpg-skip) | `pytest tests/test_game.py::test_shortlist_movie -x` | ❌ Wave 0 |
| SESS-04 | `DELETE /shortlist` clears all shortlist items | integration (asyncpg-skip) | `pytest tests/test_game.py::test_clear_shortlist -x` | ❌ Wave 0 |
| SESS-04 | `request_movie` clears shortlist as side-effect | integration (asyncpg-skip) | `pytest tests/test_game.py::test_request_movie_clears_shortlist -x` | ❌ Wave 0 |
| SESS-01+SESS-02 | `request_movie` removes saved entry for the picked movie | integration (asyncpg-skip) | `pytest tests/test_game.py::test_request_movie_removes_save -x` | ❌ Wave 0 |

All new tests use the established asyncpg-skip pattern:
```python
async def test_save_movie(client):
    try:
        import asyncpg  # noqa: F401
    except ImportError:
        pytest.skip("asyncpg not installed locally — runs in Docker")
    # ... test body using client fixture
```

### Sampling Rate
- **Per task commit:** `cd backend && pytest tests/test_game.py -x -q`
- **Per wave merge:** `cd backend && pytest tests/ -x -q`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `backend/tests/test_game.py` — append 9 new test stubs (asyncpg-skip) covering SESS-01 through SESS-04 scenarios listed above

*(Existing test file exists — append only, no new file needed)*

---

## Key Implementation Facts (Verified)

| Fact | Confidence | Source |
|------|------------|--------|
| `pg_insert` already imported in `game.py` | HIGH | Code read: `from sqlalchemy.dialects.postgresql import insert as pg_insert` |
| `Star` icon already imported in `GameSession.tsx` | HIGH | Code read: `import { X, Clock, MoreHorizontal, Shuffle, Star, ExternalLink } from "lucide-react"` |
| `ListCheck` NOT yet imported in `GameSession.tsx` | HIGH | Code read: not in current import list — needs adding |
| `queryClient.invalidateQueries` already used for eligible movies | HIGH | Code read: multiple call sites in `GameSession.tsx` |
| `filteredMovies` is a simple client-side `.filter()` chain | HIGH | Code read: lines 179–185 |
| `EligibleMovieResponse` in `game.py` does NOT yet have `saved`/`shortlisted` | HIGH | Code read: lines 132–148 |
| `request_movie` commits in one `await db.commit()` at line 1920 | HIGH | Code read: confirmed |
| Current latest Alembic revision is `0009` | HIGH | Filesystem listing confirmed |
| `from __future__ import annotations` already at top of `game.py` | HIGH | Code read: line 1 |
| Models file uses `DateTime` import from `sqlalchemy` | HIGH | Code read: `from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, UniqueConstraint` |

---

## Open Questions

1. **`saved_at` in `SessionSave` — should it be server-side `DateTime` default or `func.now()`?**
   - What we know: existing models use `mapped_column(DateTime, default=datetime.utcnow)` (Python-side default)
   - What's unclear: SQLAlchemy async sessions may not call Python defaults when using `pg_insert` directly
   - Recommendation: Add `server_default=sa.text("NOW()")` in addition to `default=datetime.utcnow` to ensure the column always has a value regardless of insertion path

2. **CONTEXT.md says "2–6 or 1" for shortlist — what does "or 1" mean exactly?**
   - What we know: CONTEXT.md says "select 2–6 movies to shortlist" and "2–6 (or 1)" in parenthetical
   - What's unclear: whether 1-item shortlist is allowed (useful for "highlight" use case) or if the filter only activates at 2+
   - Recommendation: Allow any count ≥ 1; the filter shows shortlisted items regardless of count. No minimum enforcement needed on backend.

3. **Splash dialog star icon — where exactly in the dialog header?**
   - What we know: D-03 says "corner of poster or top-right of dialog"
   - What's unclear: the current splash dialog structure (not fully read)
   - Recommendation: Read the splash dialog JSX block in `GameSession.tsx` (around line 1100–1200) during implementation planning to identify the exact insertion point.

---

## Sources

### Primary (HIGH confidence)
- `/Users/Oreo/Projects/CinemaChain/frontend/src/pages/GameSession.tsx` — existing state management, filteredMovies, mutation patterns, icon imports, table row rendering
- `/Users/Oreo/Projects/CinemaChain/frontend/src/lib/api.ts` — `EligibleMovieDTO`, `apiFetch` pattern, existing api object functions
- `/Users/Oreo/Projects/CinemaChain/frontend/src/components/MovieFilterSidebar.tsx` — `FilterState`, filter button style
- `/Users/Oreo/Projects/CinemaChain/backend/app/models/__init__.py` — `Mapped[]`, `mapped_column`, `UniqueConstraint`, `DateTime` import patterns
- `/Users/Oreo/Projects/CinemaChain/backend/app/routers/game.py` — `EligibleMovieResponse`, `get_eligible_movies`, `request_movie` commit block, `pg_insert` import
- `/Users/Oreo/Projects/CinemaChain/backend/alembic/versions/` — migration naming convention, revision chain (0009 = current head)
- `/Users/Oreo/Projects/CinemaChain/backend/tests/test_game.py` — asyncpg-skip test pattern, existing test structure

### Secondary (MEDIUM confidence)
- TanStack Query v5 `useMutation` + `onSuccess` invalidation — well-established pattern confirmed by multiple usage sites in GameSession.tsx

### Tertiary (LOW confidence)
- None — all critical claims verified from source code

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all dependencies already present; confirmed by code reads
- Architecture: HIGH — all patterns are extensions of verified existing code
- Pitfalls: HIGH — derived from direct code inspection (Tailwind purge, pg_insert, filteredMovies chain)
- Test patterns: HIGH — asyncpg-skip pattern confirmed present in test_game.py

**Research date:** 2026-03-31
**Valid until:** 2026-04-30 (stable stack; 30-day window)
