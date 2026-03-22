# Phase 5: Bug Fixes — Context

**Gathered:** 2026-03-21
**Status:** Ready for planning

<domain>
## Phase Boundary

Fix five confirmed bugs across the game chain, mobile UI, eligibility logic, CSV import, and actor load performance. One item (actor pre-cache) is a small enhancement approved for this phase. No new features beyond what's listed here.

</domain>

<decisions>
## Implementation Decisions

### BUG-1: Chain actor name missing on Eligible Movies pick

**Symptom:** When a movie is selected from the "Eligible Movies" tab without first selecting an actor, the chain history's "VIA" actor column is blank.

**Root cause (identified):** `request_movie` creates the step with `actor_tmdb_id=None, actor_name=None` when no actor was explicitly selected. `ChainHistory` looks for an actor step at `step_order + 1` — none exists.

**Expected behavior:**
- If **exactly one** eligible actor connects the previous movie to the selected movie → record that actor automatically (no user interaction needed)
- If **multiple** eligible actors connect to the selected movie → show a small inline prompt asking the user to pick which actor they're "following" (expected to be rare)
- The recorded actor must be stored as a proper actor step (with `actor_tmdb_id` and `actor_name`) so chain history renders correctly

---

### BUG-2: Mobile UI — card details and home page alignment

**Symptom 1:** Movie card details are only visible in landscape mode. In portrait mode, cards are truncated.

**Required visible fields in portrait mode:**
- Movie title
- Via actor name
- TMDB rating
- Runtime
- MPAA rating

**Symptom 2:** Buttons on the mobile home page are out of alignment.

**Fix:** Make movie cards responsive so all required fields display in any orientation. Fix home page button layout for mobile.

---

### BUG-3: Eligible movie filter logic bug

**Symptom:** After chain Dune 2 → Anya Taylor Joy → The Menu, Interstellar appeared as an eligible movie "via Timothée Chalamet" — even though Timothée Chalamet is not in The Menu.

**Correct eligibility rule (confirmed by user):**
- Eligible actors = cast of the **last watched movie only** MINUS actors already explicitly picked in this chain
- Previous chain movies have **no bearing** on next eligible actors or movies
- Only the most recently watched movie's cast (minus already-picked actors) determines what's eligible next

**Bug to investigate:** Why is Timothée Chalamet (who is not in The Menu) appearing as an eligible actor? The eligibility query may be pulling actors from chain movies beyond just the current movie. Executor should audit `get_eligible_actors` and `get_eligible_movies` queries against this rule.

---

### BUG-4: CSV import/export round-trip bug

**Symptom:** Importing a valid CSV and re-exporting produces duplicate rows and missing actor names. Confirmed with two separate chains (The Dark Knight series chain and Mean Girls). Suspected trigger: actor name spelling doesn't exactly match the DB/TMDB name.

**Fix:**
- On CSV import, validate both **movie name** and **actor name** against TMDB
- Normalize/correct names that are close but not exact (fuzzy match or TMDB lookup)
- Surface validation errors clearly if a movie or actor cannot be resolved, rather than silently creating malformed steps

---

### ENH-1: Actor selection pre-cache (approved enhancement)

**Symptom:** Selecting an eligible actor has noticeable load time before the Eligible Movies panel populates.

**Enhancement:** When a user selects an actor, immediately trigger a background pre-fetch of that actor's movie credits — so by the time the Eligible Movies panel renders, data is already in DB/cache.

**Scope:** Background fetch on actor click/selection. Does not change the actor selection UI. Similar to the existing `_prefetch_credits_background` pattern used in `request_movie`.

---

### Priority / Ordering

All 5 items are in-scope for this phase. No explicit priority ordering from user — implement as logical groupings allow. BUG-3 (eligibility logic) and BUG-1 (chain actor recording) are the most gameplay-critical. BUG-2 (mobile) and BUG-4 (CSV) are quality-of-life. ENH-1 is additive.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Game logic
- `backend/app/routers/game.py` — `request_movie`, `get_eligible_actors`, `get_eligible_movies`, `ChainHistory` step building, `_enrich_steps_thumbnails`

### Frontend chain display
- `frontend/src/components/ChainHistory.tsx` — Step rendering, VIA actor column logic (line 27: `actorStep` lookup)

### Frontend game session
- `frontend/src/pages/GameSession.tsx` — Eligible Movies/Actors tab handling, actor selection flow

### Mobile layout
- `frontend/src/components/MovieCard.tsx` — Card layout and responsive styles

### CSV import/export
- `backend/app/routers/game.py` — CSV import endpoint
- `frontend/src/pages/GameLobby.tsx` — CSV import UI

### No external specs — requirements fully captured in decisions above

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `_prefetch_credits_background` in `game.py` — existing background task pattern; ENH-1 can follow this same pattern for actor pre-cache
- `ChainHistory.tsx` — existing VIA column rendering; BUG-1 fix needs to ensure a proper actor step exists in DB so this component renders correctly
- `MovieCard.tsx` — existing card component; BUG-2 requires responsive layout changes here

### Established Patterns
- Actor steps are stored as `GameSessionStep` rows with `actor_tmdb_id IS NOT NULL` and `movie_tmdb_id` of the previous movie — BUG-1 fix must create a proper actor step (not just update existing movie step)
- `step_order` is sequential; ChainHistory looks for actor at `step_order + 1` — inserting an actor step between existing steps would reorder; solution likely requires re-evaluating step creation when no actor was explicitly chosen
- `BackgroundTasks` pattern already used in `request_movie` for credit pre-fetch — ENH-1 follows same approach

### Integration Points
- BUG-3 fix touches eligibility query in `get_eligible_actors` — must not regress the "all eligible movies without actor selected" path (Phase 03.2 Gap 3 feature)
- BUG-1 fix touches both `request_movie` (backend step creation) and potentially `GameSession.tsx` (actor prompt UI when multiple eligible actors match)
- BUG-4 fix touches CSV import endpoint — must preserve existing valid import behavior

</code_context>

<specifics>
## Specific Ideas

- BUG-1: The actor prompt (for multiple eligible actors connecting to the picked movie) should be lightweight — a small modal or inline selector, not a full-screen interruption. Expected to be rare.
- BUG-3: The fix must preserve the "show all eligible movies without actor selected" feature (Phase 03.2 Gap 3) — don't revert to requiring actor selection first
- BUG-4: User noted "Mean Girls" also exhibited the issue — actor name spelling mismatch is the likely trigger. TMDB name lookup/normalization is the preferred fix over strict exact-match validation.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 05-bug-fixes*
*Context gathered: 2026-03-21*
