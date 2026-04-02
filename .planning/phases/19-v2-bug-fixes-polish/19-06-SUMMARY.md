---
phase: 19-v2-bug-fixes-polish
plan: 06
subsystem: requirements
tags: [requirements, housekeeping, uat, gap-closure]

# Dependency graph
requires:
  - phase: 19-v2-bug-fixes-polish
    provides: All Phase 19 plans 01-05 completed (features implemented)
provides:
  - Updated REQUIREMENTS.md with accurate checkbox state for all Phase 19 requirements
  - UAT result: majority passed; 5 visual issues identified for gap closure
affects: [.planning/REQUIREMENTS.md]

# Tech tracking
tech-stack:
  added: []
  patterns: []

key-files:
  created: []
  modified:
    - .planning/REQUIREMENTS.md

key-decisions:
  - "v2BUG-01 marked complete in REQUIREMENTS.md per D-26"
  - "MDBSYNC-01/02 marked superseded — first-party Watch History replaces MDBList sync (D-27)"
  - "IMDB-01 marked partial — movie links done, actor imdb_person_id backfill deferred as cost not justified (D-28)"
  - "5 visual gap items deferred to gap closure plans — UAT found layout issues but core functionality passed"

patterns-established: []

requirements-completed: [v2BUG-01]

# Metrics
duration: 10min
completed: 2026-04-02
---

# Phase 19 Plan 06: Requirements Housekeeping & UAT Summary

**REQUIREMENTS.md updated with all Phase 19 implementation state; UAT mostly passed with 5 visual layout issues deferred to gap closure**

## Performance

- **Duration:** ~10 min
- **Completed:** 2026-04-02
- **Tasks:** 2 (1 auto + 1 checkpoint:human-verify)
- **Files modified:** 1 (.planning/REQUIREMENTS.md)

## Accomplishments

- Marked NAV-01, NAV-02, NAV-03, QMODE-06, SESS-01 through SESS-04, MDBLIST-02, SUGGEST-02, WATCHED-01 through WATCHED-03, and v2BUG-01 as `[x]` complete in REQUIREMENTS.md
- Marked MDBSYNC-01 and MDBSYNC-02 as superseded with rationale (first-party Watch History phase replaced MDBList sync)
- Marked IMDB-01 as partial — movie links point to IMDB, actor `imdb_person_id` backfill explicitly deferred
- Human UAT conducted — all core Phase 19 features verified working

## UAT Results

### Passed

- Filter reset on step advance (all filters/search/sort reset to defaults)
- Cross-page search (eligible movies searched across ALL pages, not current page only)
- NR filter toggle (NR-tagged movies hidden; movies with null MPAA remain visible)
- Sort defaults to DESC on first selection of any column
- Session menu order: Export CSV, Edit Session Name, Delete Last Step, Archive Session
- Atomic delete last step (movie + preceding actor step removed atomically; reverts to prior movie)
- Save/shortlist buttons repositioned to right side of movie cards
- Badge tooltips on hover showing source name
- Session tile step count removed
- Active session tile shows poster thumbnail next to Continue button

### Not Passed — Gap Closure Required

The following 5 visual issues were identified during UAT. They are deferred to gap closure plans and must NOT be considered regressions blocking the current plan's completion.

**GAP-01: Marked-as-Watched dialog layout**
- Current: Dialog shows "title" text and "added to radar" text inline, causing heavy text wrapping
- Required: Movie title as large heading, description text below it, "Mark as Watched" button at the bottom of the container

**GAP-02: Now Playing screen after marking watched**
- Current: Radar text still visible after a movie is marked watched
- Required: Hide radar text; show icon/rating badges instead

**GAP-03: iPhone portrait padding in play space**
- Current: Play space has excessive padding, not making full use of screen width
- Required: Reduce padding so play space uses available screen width (global nav is fine; issue is play space only)

**GAP-04: Wider screen movie tiles**
- Current: Movie selection tiles are not proportional on wider screens
- Required: Slightly taller movie selection tiles on wider screens

**GAP-05: Home page session tiles — poster and Continue button**
- Current: Poster image not showing on session tiles; Continue button is large and dominant
- Required: Poster image is the primary visual; Continue button is a de-emphasized overlay on the poster

## Task Commits

1. **Task 1: Update REQUIREMENTS.md checkboxes and notes** - `4501f1f` (chore)
2. **Task 2: Human verification checkpoint** - No commit (human action; result: issues found, see gap items above)

## Files Created/Modified

- `.planning/REQUIREMENTS.md` — NAV, QMODE-06, SESS, MDBLIST-02, SUGGEST-02, WATCHED reqs marked `[x]`; MDBSYNC superseded; IMDB-01 partial; v2BUG-01 complete

## Deviations from Plan

None for executed tasks. Task 1 completed exactly as specified. Task 2 (human checkpoint) returned issues — those are tracked as gap items above, not plan deviations.

## Known Stubs

None in files modified by this plan.

## Next Steps

Gap closure plans needed for 5 visual issues (GAP-01 through GAP-05) identified in UAT. Phase 19 core work is complete; the gap items are polish/layout concerns.

---
*Phase: 19-v2-bug-fixes-polish*
*Completed: 2026-04-02*
