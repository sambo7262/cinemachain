---
phase: 08-bug-fixes
verified: 2026-03-31T04:00:00Z
status: passed
score: 11/11 must-haves verified
re_verification: false
---

# Phase 8: Bug Fixes Verification Report

**Phase Goal:** Resolve all known UX friction and data gaps before adding new features.
**Verified:** 2026-03-31T04:00:00Z
**Status:** PASSED
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | MPAA rating displays "NR" for both null and "" in table cell, splash dialog, and MovieCard | VERIFIED | `movie.mpaa_rating \|\| "NR"` at GameSession.tsx:988; `splashMovie?.mpaa_rating \|\| "NR"` at :1077; `mpaa_rating \|\| "NR"` at MovieCard.tsx:84 |
| 2 | RT score displays "—" em dash when null/zero in movies table and splash dialog | VERIFIED | Ternary `movie.rt_score ? \`🍅 ...\` : "—"` at GameSession.tsx:991; same pattern for splash at :1074 |
| 3 | Missing overview shows "No overview available." in splash dialog — never blank | VERIFIED | `splashMovie?.overview \|\| "No overview available."` at GameSession.tsx:1093 inside unconditional `<p>` |
| 4 | Nightly cache job backfills overview for movies where overview IS NULL | VERIFIED | `_backfill_overview_pass` defined at cache.py:127; called from `nightly_cache_job` at :256; query uses `Movie.overview.is_(None)` at :131 |
| 5 | Actor name in tab bar is truncated and never bleeds outside its container | VERIFIED | `max-w-[160px] truncate inline-block align-middle` at GameSession.tsx:677; parent TabsTrigger has `overflow-hidden` at :674 |
| 6 | GameLobby session tile stat text wraps or truncates on narrow screens | VERIFIED | `flex flex-wrap gap-x-1` on stat paragraph at GameLobby.tsx:231; `min-w-0` on left column div at :221 |
| 7 | Now Playing movie title wraps cleanly and does not overflow its flex container | VERIFIED | `break-words` at GameSession.tsx:556; `min-w-0` on text column div at :554 |
| 8 | Movies table title column is sticky on horizontal scroll with readable background | VERIFIED | `sticky left-0 bg-muted/50 z-10` on poster th at :899; `sticky left-14 bg-muted/50 z-10` on title th at :900; body td equivalents at :946, :957 |
| 9 | Eligible movies list shows prev/next pagination instead of Load More button | VERIFIED | `setMoviesPage((p) => p - 1)` at :1006; `Page {moviesPage} of {eligibleMoviesTotalPages}` at :1012; "Load more" absent; `allEligibleMovies = eligibleMoviesData?.items ?? []` at :162 |
| 10 | ChainHistory table shows 20 steps per page with prev/next controls | VERIFIED | `PAGE_SIZE = 20` at ChainHistory.tsx:7; `pagedSteps` slice at :37; `filteredSteps.map` replaced by `pagedSteps.map` at :60; controls at :153, :164 |
| 11 | CSV export handles step_order gaps; eligible movies self-heals missing credits | VERIFIED | Forward-scan `s.step_order > step.step_order and s.actor_tmdb_id is not None` at game.py:1043; `step_by_order` dict absent; self-heal block at :1558–1565; regression test at test_game.py:1613 |

**Score:** 11/11 truths verified

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `frontend/src/pages/GameSession.tsx` | Table cell MPAA NR; RT em dash; splash always-render; pagination controls; sticky table; mobile overflow fixes | VERIFIED | All patterns confirmed via grep |
| `frontend/src/components/MovieCard.tsx` | MPAA badge always renders with NR fallback | VERIFIED | Line 84: `mpaa_rating \|\| "NR"` |
| `backend/app/services/cache.py` | `_backfill_overview_pass` defined and called from nightly job | VERIFIED | Definition at line 127, call site at line 256 |
| `frontend/src/pages/GameLobby.tsx` | Session tile stat row wraps on mobile; left column min-w-0 | VERIFIED | `flex-wrap` at line 231; `min-w-0` at line 221 |
| `frontend/src/components/ChainHistory.tsx` | PAGE_SIZE=20 pagination with prev/next controls | VERIFIED | PAGE_SIZE, pagedSteps, setPage all present |
| `backend/app/routers/game.py` | CSV forward-scan fix; eligible-movies self-heal | VERIFIED | Forward-scan at line 1043; self-heal block at lines 1558–1565 |
| `backend/tests/test_game.py` | Regression test for BUG-08 step_order gap | VERIFIED | `test_csv_export_with_step_order_gap` at line 1613 |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `movie.mpaa_rating` (table cell) | Displayed text | `\|\| "NR"` — empty string and null both fall through | WIRED | GameSession.tsx:988 confirmed |
| `splashMovie?.overview` (splash dialog) | Displayed paragraph | Always-render `<p>` with `\|\|` fallback | WIRED | GameSession.tsx:1092–1094 — unconditional `<p>` confirmed |
| `_backfill_overview_pass` (cache.py) | `nightly_cache_job` | Called after `_backfill_mpaa_pass` | WIRED | cache.py:256 confirmed |
| `selectedActor.name` (tab bar span) | Displayed text | `max-w-[160px] truncate` + parent `overflow-hidden` | WIRED | GameSession.tsx:674, 677 confirmed |
| `movie title` (Now Playing) | Displayed paragraph | `break-words` + `min-w-0` on parent | WIRED | GameSession.tsx:554, 556 confirmed |
| Title th/td (movies table) | Sticky left column | `sticky left-14 bg-muted/50`/`bg-card` | WIRED | GameSession.tsx:900, 957 confirmed |
| `eligibleMoviesData?.items` (GameSession) | Displayed movies list | Direct assignment — no accumulation | WIRED | GameSession.tsx:162 confirmed; `accumulatedMovies` fully absent |
| `moviesPage` state | Prev/next controls | `setMoviesPage((p) => p - 1)` and `p + 1` | WIRED | GameSession.tsx:1006, 1014 confirmed |
| `filteredSteps` (ChainHistory) | Paginated slice | `filteredSteps.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE)` | WIRED | ChainHistory.tsx:37 confirmed |
| `export_session_csv` actor lookup | Correct actor name | Forward-scan `next()` over sorted_steps | WIRED | game.py:1040–1044 confirmed; `step_by_order` dict absent |
| `eligible_actor_tmdb_ids` empty check | Self-heal re-fetch | `_ensure_movie_cast_in_db` called when no credits | WIRED | game.py:1555–1565 confirmed |

---

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| BUG-01 | 08-02-PLAN | Mobile UI renders correctly at 320–768px across all game views | SATISFIED | truncate, break-words, sticky cols, flex-wrap all implemented |
| BUG-02 | 08-01-PLAN | MPAA rating displays for all movies with available TMDB data | SATISFIED | `\|\| "NR"` in all 3 display locations |
| BUG-03 | 08-01-PLAN | Movie overview populates in splash dialog for all movies | SATISFIED | Always-render `<p>` + nightly backfill for stale NULL rows |
| BUG-04 | 08-03-PLAN | Chain history and movie search results paginate correctly | SATISFIED | Load More replaced; ChainHistory PAGE_SIZE=20 |
| BUG-05 | 08-03-PLAN | Eligible movies sort order is stable when new movies dynamically loaded | SATISFIED | Accumulation removed — each page is an independent server-side slice |
| BUG-06 | 08-01-PLAN | Movies with valid TMDB entries show RT score or explicit N/A — never blank | SATISFIED | RT em dash in table cell and splash dialog |
| BUG-07 | 08-04-PLAN | Session-specific: eligible movies display correctly (Trainspotting chain) | SATISFIED | Self-heal re-fetch block in combined-view eligible movies |
| BUG-08 | 08-04-PLAN | Session-specific: CSV export succeeds for affected session | SATISFIED | Forward-scan replaces step_order+1 assumption; regression test added |

All 8 requirements verified. No orphaned requirements.

---

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| — | — | None found | — | — |

No stubs, placeholders, or empty implementations detected in phase-modified files. All accumulation state (`accumulatedMovies`, `prevAccumulatedCountRef`, `firstNewResultRef`) fully removed. `step_by_order` dict removed from CSV export path.

---

### Human Verification Required

#### 1. Mobile overflow visual confirmation

**Test:** Open the app at 375px viewport width (iPhone SE). Navigate to an active game session. Select an actor with a long name and observe the tab bar.
**Expected:** The "via {actor name}" span truncates with an ellipsis and does not bleed outside the tab trigger.
**Why human:** CSS truncation only verifiable by visual inspection; cannot confirm ellipsis rendering via grep.

#### 2. GameLobby tile stat wrapping

**Test:** Open GameLobby at 375px viewport. Look at a session tile with a long runtime and date.
**Expected:** Stat text wraps to two lines rather than overflowing the tile boundary.
**Why human:** `flex-wrap` behavior requires browser layout engine to verify wrapping occurs at the right breakpoint.

#### 3. Movies table sticky column during scroll

**Test:** Open the eligible movies tab in a game session. Scroll the table horizontally on a narrow screen.
**Expected:** Poster and title columns remain fixed while other columns scroll behind them; backgrounds prevent content bleed-through.
**Why human:** Sticky positioning depends on scroll container geometry; CSS classes confirmed but visual result needs browser verification.

#### 4. BUG-07 Trainspotting session self-heal

**Test:** On the NAS instance, load the Trainspotting chain session and navigate to the eligible movies tab.
**Expected:** Eligible movies now appear (self-heal re-fetch triggered on first load if credits were missing).
**Why human:** This is a session-specific data repair; the specific NAS session state cannot be queried programmatically from this environment. The code path is wired and correct; the actual session data outcome requires live testing.

---

### Commit Verification

All 14 task commits and 2 docs commits confirmed present in git history:

| Commit | Plan | Description |
|--------|------|-------------|
| 6701322 | 08-01 | MPAA table cell NR fallback, RT table cell em dash |
| 4c363b5 | 08-01 | Splash dialog always-render MPAA NR, RT em dash, overview fallback |
| a7a7393 | 08-01 | MovieCard MPAA badge always renders with NR fallback |
| 470a0db | 08-01 | Add `_backfill_overview_pass` to nightly cache job |
| 70c51cb | 08-02 | Truncate actor name in "via {name}" tab label |
| d1dfa8b | 08-02 | Fix Now Playing movie title overflow |
| 489d99c | 08-02 | Add sticky poster and title columns to movies table |
| 5dc28e1 | 08-02 | Fix GameLobby session tile stat text overflow |
| cbd7649 | 08-03 | Remove accumulation state; direct eligibleMoviesData.items assignment |
| c9d33ba | 08-03 | Replace Load More with prev/next pagination |
| 61bf13e | 08-03 | Add pagination to ChainHistory (20 steps/page) |
| 4ff55ec | 08-04 | Replace step_order+1 assumption with forward-scan in CSV export |
| d09abbd | 08-04 | Self-heal combined-view eligible movies when current movie has no credits |
| 9af7081 | 08-04 | Regression test for CSV export step_order gap (BUG-08) |

---

## Summary

Phase 8 goal achieved. All 8 requirements (BUG-01 through BUG-08) are implemented and wired in the codebase. No missing artifacts, no stubs, no orphaned requirements.

Key verifications:
- Missing-data display convention is uniform across all three locations (table cell, splash dialog, MovieCard) — `||` operator correctly handles both `null` and `""` sentinel for MPAA; ternary handles RT; unconditional `<p>` with `||` handles overview.
- Accumulation state entirely absent from GameSession.tsx — the sort stability bug cannot recur.
- CSV export forward-scan is present and `step_by_order` dict is gone — the fragile assumption is eliminated.
- Self-heal block is wired into the combined-view eligible movies path — missing credits trigger re-fetch on demand.
- 4 human verification items identified for visual/live-session confirmation; all automated checks pass.

---

_Verified: 2026-03-31T04:00:00Z_
_Verifier: Claude (gsd-verifier)_
