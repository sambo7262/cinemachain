---
phase: 10-query-mode
plan: "01"
subsystem: testing
tags: [wave-0, tdd, stubs, search, query-mode]
dependency_graph:
  requires: []
  provides: [test-stubs-qmode-01, test-stubs-qmode-02, test-stubs-qmode-03, test-stubs-qmode-04, test-stubs-qmode-05, test-stubs-qmode-06]
  affects: [backend/tests/test_search.py, frontend/src/pages/__tests__/SearchPage.test.tsx]
tech_stack:
  added: []
  patterns: [asyncpg-skip-stub, vitest-null-stub-component]
key_files:
  created:
    - backend/tests/test_search.py
    - frontend/src/pages/SearchPage.tsx
    - frontend/src/pages/__tests__/SearchPage.test.tsx
  modified: []
decisions:
  - "SearchPage.tsx null stub created alongside test file because Vite 6 resolves dynamic imports at transform time — vi.mock hoisting cannot suppress file-not-found errors from the vite:import-analysis plugin; a real (minimal) file is required for tests to collect"
metrics:
  duration_minutes: 12
  completed_date: "2026-03-31T17:44:57Z"
  tasks_completed: 2
  files_changed: 3
---

# Phase 10 Plan 01: Wave 0 Test Stubs Summary

Wave 0 test infrastructure for Phase 10 (Query Mode) — 4 backend pytest stubs and 5 frontend vitest stubs providing named test targets for all Wave 1+ verification commands.

## What Was Built

### backend/tests/test_search.py
Four `@pytest.mark.asyncio` stub tests using the same asyncpg-skip pattern established in `conftest.py`. Each test calls `pytest.skip(...)` immediately, so the suite collects cleanly (4 SKIPPED, 0 ERROR, exit 0) without a live DB or TMDB key.

| Test function | Requirement |
|---|---|
| `test_search_movies_enriched` | QMODE-01 |
| `test_search_actors` | QMODE-02 |
| `test_popular_by_genre` | QMODE-03 |
| `test_request_movie_standalone` | QMODE-06 |

### frontend/src/pages/__tests__/SearchPage.test.tsx
Five vitest stubs across two `describe` blocks, with the `@/lib/api` mock wired in place so it is ready for real assertions in Wave 2.

| Test | Requirement |
|---|---|
| renders results table after title search | QMODE-04 |
| sort by year ascending puts oldest movie first | QMODE-04 |
| null values sort to bottom regardless of sort direction | QMODE-04 |
| shows all movies when toggle is 'All' | QMODE-05 |
| hides watched movies when toggle is 'Unwatched Only' | QMODE-05 |

### frontend/src/pages/SearchPage.tsx (deviation — see below)
Minimal null-returning component stub. Required by the Vite 6 transform step (see Deviations).

## Verification Results

```
backend: 4 skipped in 0.03s   (exit 0)
frontend: 5 passed in 1.63s   (exit 0)
```

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking Issue] Vite 6 transform-time resolution failure on missing SearchPage.tsx**

- **Found during:** Task 2 verification
- **Issue:** The plan's recommended pattern (`try { await import("@/pages/SearchPage") } catch { return }`) does not work with Vite 6 + vitest 4. The `vite:import-analysis` plugin resolves aliases during the _transform_ phase — before vitest's `vi.mock` hoisting or any runtime `try/catch` can intercept. The result: `Failed to resolve import "@/pages/SearchPage"` at build time, 0 tests collected, exit 1.
- **Fix:** Created `frontend/src/pages/SearchPage.tsx` as a minimal null-returning component stub. The test file imports it directly (no try/catch needed). Wave 2 (Plan 10-03) replaces this stub with the real implementation.
- **Files modified:** `frontend/src/pages/SearchPage.tsx` (created), `frontend/src/pages/__tests__/SearchPage.test.tsx` (import style updated)
- **Commit:** 573dec0

## Known Stubs

| File | Description | Resolved by |
|---|---|---|
| `frontend/src/pages/SearchPage.tsx` | Returns `null` — no UI | Plan 10-03 (Wave 2) |

The SearchPage.tsx stub is intentional and expected. It exists solely to satisfy Vite's module resolver. All 5 test assertions are trivially true (`expect(document.body).toBeTruthy()`) and will be replaced with real behavior assertions when Wave 2 lands.

## Self-Check: PASSED

- `backend/tests/test_search.py` — exists, 4 tests, all SKIPPED
- `frontend/src/pages/__tests__/SearchPage.test.tsx` — exists, 5 tests, all passed
- `frontend/src/pages/SearchPage.tsx` — exists (Wave 0 stub)
- Commit `573dec0` — verified in git log
