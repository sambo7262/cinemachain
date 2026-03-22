---
phase: 05-bug-fixes
verified: 2026-03-21T00:00:00Z
status: gaps_found
score: 3/5 must-haves verified
gaps:
  - truth: "MovieCard renders title, via actor, TMDB rating, runtime, and MPAA badge in portrait mobile (320px width)"
    status: failed
    reason: "Human verification confirmed portrait mode shows only movie info and landscape shows only actor info. The Eligible Movies view is a responsive table (not MovieCard components), and the table hides via_actor_name (hidden sm:table-cell) in portrait and hides rating/runtime (hidden lg:table-cell) in both portrait and landscape. The min-w-0 + line-clamp-2 fix applied to MovieCard.tsx has no effect on the Eligible Movies table layout."
    artifacts:
      - path: "frontend/src/pages/GameSession.tsx"
        issue: "Eligible Movies tab renders a <table> with hidden sm:table-cell and hidden lg:table-cell columns — portrait mode loses via_actor_name, landscape loses rating/year/runtime/MPAA. MovieCard is not used here."
    missing:
      - "Eligible Movies table needs mobile-aware column visibility or a card layout for narrow screens so all required fields are visible in portrait"
  - truth: "CSV import correctly links all movies to their actors via TMDB lookups; mismatched names are flagged with clear errors"
    status: failed
    reason: "Human verification confirmed display issues for specific imported sessions. Root cause: actor name spelling mismatches and incorrect movie titles cause TMDB lookup failures during import — _resolve_actor_tmdb_id returns None, leaving actor_tmdb_id null in the DB. The import currently silently fails with no validation feedback. 10 specific errors identified in user's 136-row CSV: 6 actor spelling errors (Nestor Carbonell, Philip Baker Hall, Demián Bichir, Frances Fisher, Amy Poehler, J. P. Manoux) and 4 movie title errors (The Dark Knight, The Dark Knight Rises, Kill Bill: The Whole Bloody Affair, Pulp Fiction). Additionally, 2 entries reference actors not credited in those films on TMDB (row 113: Aylam Orian / IDR, row 114: Kyle Mclean / Black Widow)."
    artifacts:
      - path: "backend/app/routers/game.py"
        issue: "_resolve_actor_tmdb_id returns (None, None) silently when actor name doesn't match TMDB. import_csv_session stores null actor_tmdb_id without raising an error or warning. No movie title fuzzy-match or validation step exists."
    missing:
      - "CSV import must validate each row: movie title must resolve to a TMDB movie ID, and actor name must match a credited actor in that film. Rows that fail validation should be returned as errors with specific mismatch details rather than silently imported with null values."
---

# Phase 5: Bug Fixes Verification Report

**Phase Goal:** Fix BUG-1 (auto-resolve connecting actor), BUG-2 (mobile layout), BUG-3 (eligibility scoping), BUG-4 (CSV canonical names), and ENH-1 (actor pre-fetch) — all verified against the live NAS deployment.
**Verified:** 2026-03-21
**Status:** gaps_found
**Re-verification:** No — initial verification

Human verification results provided as authoritative input for BUG-1, BUG-3, ENH-1 (PASS), BUG-4 data integrity (PASS), BUG-2 MovieCard (PARTIAL — confirmed open), and CSV import display (NEW GAP — confirmed open). Automated code verification performed for all codebase artifacts.

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Selecting a movie without prior actor pick auto-records the connecting actor (BUG-1) | VERIFIED | `disambiguation_required` logic in game.py line 1696; `disambigOpen` state + dialog in GameSession.tsx line 982; human verified PASS |
| 2 | MovieCard renders title, via actor, rating, runtime, MPAA badge in portrait mobile (BUG-2) | FAILED | Eligible Movies view is a table with `hidden sm:table-cell` / `hidden lg:table-cell` — portrait hides via_actor_name; human verified PARTIAL |
| 3 | Eligible actors shown are only from current movie's cast (BUG-3) | VERIFIED | Eligibility query scoped to `current_movie_tmdb_id`; ELIGIBILITY SCOPE INVARIANT comment added; human verified PASS |
| 4 | CSV import stores canonical TMDB actor names; imported sessions display correctly (BUG-4) | PARTIAL | `_resolve_actor_tmdb_id` returns tuple (canonical name stored — PASS); but imported sessions display broken in UI (FAIL) |
| 5 | Actor selection loads eligible movies faster than before (ENH-1) | VERIFIED | `_prefetch_actor_credits_background` added at line 532; wired into `pick_actor` via `background_tasks.add_task` at line 1604; human verified PASS |

**Score:** 3/5 truths fully verified (BUG-1, BUG-3, ENH-1 PASS; BUG-2 and CSV display FAIL)

---

## Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `backend/tests/test_game.py` | Six asyncpg-skip test stubs | VERIFIED | All six function names present at lines 1035, 1102, 1175, 1258, 1310, 1423 |
| `backend/app/routers/game.py` | BUG-3 scope comments, BUG-4 canonical tuple, ENH-1 background task, BUG-1 auto-resolve | VERIFIED | All patterns confirmed (see key links below) |
| `frontend/src/pages/GameSession.tsx` | BUG-1 disambiguation dialog | VERIFIED | `disambigOpen` state at line 60; `Who are you following?` at line 985; `disambiguation_required` check at line 229 |
| `frontend/src/components/MovieCard.tsx` | BUG-2 responsive portrait layout | PARTIAL | `min-w-0` at line 66 and `line-clamp-2` at line 67 present, but MovieCard is not used in Eligible Movies view — the table view lacks mobile field visibility |
| `frontend/src/pages/GameLobby.tsx` | BUG-2 button alignment fix | VERIFIED | `flex flex-wrap items-center gap-2` at line 243; `w-full sm:w-auto` at line 272 |
| `frontend/src/lib/api.ts` | `skip_actor` parameter in requestMovie | VERIFIED | `skip_actor?: boolean` at line 145 |

---

## Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `pick_actor` handler | `_prefetch_actor_credits_background` | `background_tasks.add_task` | WIRED | Line 1604: `background_tasks.add_task(_prefetch_actor_credits_background, body.actor_tmdb_id, tmdb)` |
| `_resolve_actor_tmdb_id` | `import_csv_session steps_data` | canonical name tuple return | WIRED | Line 719: `"actor_name": canonical_name or row.actorName` |
| `request_movie` | `GameSessionStep (actor step)` | auto-actor resolution query | WIRED | Lines 1661-1725: shared actor query + auto-create at `existing_max+1` |
| `request_movie response` | `GameSession handleMovieConfirm` | `disambiguation_required` status check | WIRED | GameSession.tsx line 229: `if (requestResult?.status === "disambiguation_required")` |
| `handleDisambigSkip` | `api.requestMovie skip_actor: true` | skip_actor parameter | WIRED | GameSession.tsx line ~308: `skip_actor: true` in handleDisambigSkip body |
| CSV row (movie, actor) | TMDB credit link | `_resolve_actor_tmdb_id` + movie title lookup | NOT WIRED | Spelling mismatches produce null actor_tmdb_id silently; no validation or error feedback returned to caller |

---

## Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|---------|
| BUG-1 | 05-01, 05-03, 05-04 | Auto-resolve connecting actor; disambiguation dialog | SATISFIED | Backend: `skip_actor` + auto-resolve in `request_movie`; Frontend: disambiguation dialog; human PASS |
| BUG-2 | 05-04 | Mobile layout for MovieCard and GameLobby | BLOCKED | GameLobby button fix verified (PASS); MovieCard fix does not address Eligible Movies table — human PARTIAL |
| BUG-3 | 05-01, 05-02 | Eligibility scoped to current movie's cast | SATISFIED | Query confirmed scoped; scope invariant comment added; human PASS |
| BUG-4 | 05-01, 05-02 | CSV canonical TMDB names; no duplicates on round-trip | BLOCKED | Data integrity PASS; CSV session display rendering broken — human confirmed new gap |
| ENH-1 | 05-01, 05-02 | Actor pre-fetch background task on pick_actor | SATISFIED | `_prefetch_actor_credits_background` defined and wired; human PASS |

---

## Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `backend/app/routers/game.py` | `import_csv_session` | No row-level validation — null actor_tmdb_id stored silently on TMDB lookup failure | Blocker | Misspelled actor names and wrong movie titles fail silently; imported sessions have broken chain data |
| `frontend/src/pages/GameSession.tsx` | 902-903 | `via_actor_name` in Eligible Movies table uses `hidden sm:table-cell` | Blocker | Portrait mobile hides actor info column entirely; not addressable by MovieCard CSS fixes |

---

## Human Verification Results (Provided)

The following items were verified by the user on the live NAS deployment:

| Item | Result |
|------|--------|
| BUG-1: Actor auto-resolve / disambiguation dialog | PASS |
| BUG-3: Eligibility scoped to current movie cast only | PASS |
| ENH-1: Actor pre-fetch speed improvement | PASS |
| BUG-4: CSV round-trip data integrity | PASS |
| BUG-2: GameLobby session button width | PASS |
| BUG-2: MovieCard portrait/landscape layout | PARTIAL — portrait shows only movie info, landscape shows only actor info |
| CSV import validation: mismatched actor/title names flagged with errors | FAIL — 10 errors in 136-row CSV silently imported with null actor_tmdb_id values |

---

## Gaps Summary

Two items are confirmed open by human verification and corroborated by code analysis:

**Gap 1 — BUG-2 MovieCard (portrait/landscape):** The `min-w-0` and `line-clamp-2` fixes applied to `MovieCard.tsx` (05-04) do not affect the Eligible Movies view, which renders as a `<table>` in `GameSession.tsx`, not as `MovieCard` components. The table hides `via_actor_name` (`hidden sm:table-cell`) in portrait, and hides rating/year/runtime/MPAA (`hidden lg:table-cell`) in most viewport sizes. The fix was applied to the wrong component; the table layout itself needs mobile-aware visibility adjustments.

**Gap 2 — CSV import validation:** Actor name spelling mismatches and incorrect movie titles silently produce null `actor_tmdb_id` values during import, causing imported sessions to display incorrectly. Human verification identified 10 concrete errors in a 136-row CSV file (6 actor spelling errors, 4 movie title errors) that would all fail silently. The import endpoint needs row-level validation: each (movie title, actor name) pair must resolve to a real TMDB credit. Rows that fail should be returned as structured errors with specific mismatch details so the user can correct their CSV before re-importing.

---

_Verified: 2026-03-21_
_Verifier: Claude (gsd-verifier)_
