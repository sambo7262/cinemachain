# Phase 8 Context — Bug Fixes

**Phase goal:** Resolve all known UX friction and data gaps before adding new features.
**Requirements:** BUG-01 through BUG-08

---

## Area A: Missing data display convention
*(BUG-02 MPAA · BUG-03 overview · BUG-06 RT score)*

### Decisions

- **Missing RT score** → display `—` (em dash). Never blank.
- **Missing MPAA** → display `NR` badge. Maps backend `""` (no US cert) and `None` (never fetched) both to `NR`. The MPAA filter sidebar already includes "NR" as an option — this aligns with that expectation.
- **Missing overview** → display `"No overview available."` in the splash dialog. Never collapse the space silently.
- **Rule is uniform** — all three missing-data states follow the same explicit-placeholder principle.

### Nightly backfill job (new requirement)
Some missing data is due to stale DB records from earlier builds before these fields were populated. Extend the nightly cache job to:
- Backfill `mpaa_rating IS NULL` — fetch `/movie/{id}/release_dates` from TMDB for each affected movie
- Backfill `overview IS NULL` — fetch `/movie/{id}` from TMDB for each affected movie
- All movies should have MPAA and overview; RT score may legitimately be absent (not all titles are on MDBList)

### Code context
- Backend sentinel values: `mpaa_rating = ""` means "fetched, no US cert"; `rt_score = 0` means "MDBList returned no result"
- `_fetch_mpaa_rating` in `backend/app/routers/game.py:217–251` — called on-demand; needs to also run in nightly job
- Overview fetch: no on-demand path currently exists — nightly backfill is the right place
- Frontend display: `MovieCard.tsx:83–86`, `GameSession.tsx:1012` (table cell), `GameSession.tsx:1085–1112` (splash dialog)

---

## Area B: Mobile UI scope and table treatment
*(BUG-01)*

### Decisions

- **In-scope views:** All in-session views (GameSession page — all tabs) + Settings page + GameLobby (session grid). Splash dialog excluded — user confirmed it works fine on mobile.
- **Priority fixes identified by user:**
  1. Now Playing screen — text wrapping issues
  2. GameLobby session tiles — stat text overflows tile container
  3. Actor name overflow — after an actor is selected, their name bleeds outside its container to the right of the page
- **Eligible movies table:** Keep horizontal scroll (`overflow-x-auto`) but add polish — sticky title column, subtle scroll shadow/indicator so the scroll is discoverable
- **Filter sidebar:** Keep current toggle behavior, light polish only (no redesign to bottom sheet)
- **Splash dialog:** No changes — working correctly on mobile

### Code context
- Actor name overflow: `GameSession.tsx` — actor display after selection, likely missing `truncate` or `min-w-0` in a flex container
- Session tile stats: `GameLobby.tsx` — tile stat layout
- Now Playing text wrapping: `GameSession.tsx` Now Playing section — likely missing `break-words` or `truncate`
- Table: `GameSession.tsx:918` — `<table className="min-w-max w-full text-sm">` inside `overflow-x-auto` container, sticky first column needs `sticky left-0 bg-background z-10`

---

## Area C: Pagination model
*(BUG-04 BUG-05)*

### Decisions

- **Replace "Load More" with standard page navigation** — page controls (prev / next, current page indicator), 20 movies per page
- All movies are fetched and sorted on the backend upfront; frontend just displays the current page slice — no accumulation logic
- This eliminates the sort stability problem: each page fetch is now a clean "give me page N of the full sorted list" request
- **Chain history gets the same treatment** — paginate at 20 steps/page. Confirmed needed: one session has 100+ movies.
- **Search behavior unchanged** — search returns all matching results across the full dataset regardless of current page. Current backend behavior (bypasses pagination when search string present) is correct and preserved.
- **Sort/filter change resets to page 1** — already the intent, now clean to implement since there's no accumulation state to clear

### Implementation notes
- Backend pagination endpoint already exists and is correct — only the frontend "Load More" / accumulation pattern needs replacing
- `accumulatedMovies` state and `prevAccumulatedCountRef` can be removed
- Page controls: simple prev/next with page X of Y display is sufficient — no need for jump-to-page input
- `moviesPage` state remains; query key `[..., moviesPage]` remains; only the accumulation effect and Load More button are replaced

### Code context
- Frontend accumulation: `GameSession.tsx:151–182` (query), effect at ~177–178 (append logic to replace), Load More button at `GameSession.tsx:1024–1035`
- ChainHistory: `frontend/src/components/ChainHistory.tsx` — currently no pagination, renders all steps

---

## Area D: Session-specific bug investigation
*(BUG-07 BUG-08)*

### Decisions

- **Both broken sessions are reproducible on the NAS** — Trainspotting chain and the CSV export failure session are still present and testable
- **Fix strategy: investigate + repair + harden** — diagnose the specific sessions, repair their data if fixable via SQL/API, AND fix the underlying logic so the same class of failure can't happen to future sessions
- **BUG-07 (Trainspotting chain — no eligible movies):** Session has corrupted/deleted steps but is otherwise intact. The 100+ movie chain works fine, so the issue is session-specific data state, not a global logic bug. Investigate: inspect the session's steps in the DB, check `current_movie_tmdb_id`, check that the current movie's actor credits are in the DB
- **BUG-08 (CSV export — internal server error):** Server already returns a 500 with logging — no additional error toast needed. Fix should address the root cause (likely a broken step sequence assumption: `step.step_order + 1` assumes the next step is always the actor step). Make CSV export defensive against missing/out-of-order steps
- **No new error UX for CSV** — the existing 500 response with server-side logging is sufficient. User can retry.

### Code context
- CSV export: `backend/app/routers/game.py:1019–1051` — the `actor_step = step_by_order.get(step.step_order + 1)` assumption is fragile; replace with a lookup that finds the next actor step after each movie step regardless of gaps in step_order
- Eligible movies query: `backend/app/routers/game.py:1464–1568` — combined view builds eligible actor list from `current_movie_tmdb_id`; if that movie's credits aren't in DB, eligible actors list is empty → no movies shown
- Diagnostic approach: connect to DB on NAS, inspect the Trainspotting session's `game_session_steps` rows and `current_movie_tmdb_id` to identify the corruption

---

## Code context summary

| Bug | Key file(s) | Root cause (known) |
|-----|-------------|-------------------|
| BUG-01 | `GameSession.tsx`, `GameLobby.tsx`, `NavBar.tsx` | Missing flex constraints, no truncate on actor name, tile overflow |
| BUG-02 | `game.py:217–251`, `MovieCard.tsx:83–86` | `""` sentinel not mapped to `NR`; nightly backfill missing |
| BUG-03 | `GameSession.tsx:1107–1112`, nightly job | No on-demand overview fetch; stale DB records |
| BUG-04 | `GameSession.tsx:151–182`, `ChainHistory.tsx` | Accumulation replaced by pagination; chain history needs paging |
| BUG-05 | `GameSession.tsx:117–136` | Resolved by pagination model — no more accumulation |
| BUG-06 | `GameSession.tsx:1015`, `game.py:1593–1605` | `null` rt_score renders blank; replace with `—` |
| BUG-07 | `game.py:1464–1568` | Corrupted session state; current movie credits likely missing from DB |
| BUG-08 | `game.py:1019–1051` | Step order assumption fragile; fix + investigate specific session |
