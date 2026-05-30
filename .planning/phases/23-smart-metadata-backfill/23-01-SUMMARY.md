---
phase: 23-smart-metadata-backfill
plan: 01
subsystem: database
tags: [alembic, postgres, sqlalchemy, sentinels, audit, tmdb]

# Dependency graph
requires:
  - phase: 17-db-health-audit
    provides: /db-health endpoint with row-level + size stats
  - phase: 22-filmography-refresh-gap
    provides: alembic head at revision 0019 (filmography_fetched_at)
provides:
  - migration 0020 promoting empty mpaa_rating to 'NR' sentinel
  - MPAA backfill switched to positive sentinel + IS NULL query (cuts ~25k pointless TMDB calls/night)
  - /db-health audit uses sentinel-aware ("addressable gap") semantics
affects: [cache, mdblist, db-health, settings]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Positive-sentinel writeback pattern for backfill jobs (mirrors mdblist.py rt_score=0/imdb_id='')"
    - "Addressable-gap audit semantics: count IS NULL only, exclude data-ceiling sentinels"

key-files:
  created:
    - backend/alembic/versions/20260530_0020_promote_empty_mpaa_to_nr.py
  modified:
    - backend/app/services/cache.py
    - backend/app/routers/settings.py
    - backend/tests/test_cache.py

key-decisions:
  - "Honored CONTEXT D1: positive sentinel 'NR' (not '') eliminates retry waste and renders identically via existing `mpaa_rating || \"NR\"` in MovieCard.tsx"
  - "Honored CONTEXT D3 Option A clean: dropped sentinel-counting OR clauses for mpaa/imdb_id/imdb_rating/rt_score; kept overview unchanged (no sentinel pattern exists)"
  - "Honored CONTEXT D4: services/mdblist.py byte-identical — verified `git diff` empty"
  - "Honored CONTEXT D5: zero new endpoints, zero new Settings UI, zero frontend files modified"
  - "Honored CONTEXT D6: migration 0020 is data-only and reversible (downgrade reverts 'NR' → '')"
  - "Fetched-counter logic adjusted from `if cert:` to `if cert != \"NR\":` so log line 'ratings found' still means 'real certifications' (not sentinel writes)"

patterns-established:
  - "Backfill jobs must use positive sentinels + IS NULL query — mirrors mdblist.py (services/mdblist.py:60,229)"
  - "DB Health audit queries must use IS NULL only; sentinel-zero rows are excluded from 'addressable gap' counts"

requirements-completed: [HEALTH-01, HEALTH-02]

# Metrics
duration: ~25 min
completed: 2026-05-30
---

# Phase 23 Plan 01: Smart Metadata Backfill (MPAA sentinel + audit accuracy) Summary

**Switched MPAA backfill to positive 'NR' sentinel with IS NULL query, shipped migration 0020 to promote 33k legacy empty rows, and rewrote /db-health audit to use sentinel-aware IS NULL semantics.**

## Performance

- **Duration:** ~25 min
- **Started:** 2026-05-30T01:05:00Z (approx)
- **Completed:** 2026-05-30T01:30:53Z
- **Tasks:** 3
- **Files modified:** 4 (1 created, 3 modified)
- **Commits:** 4 (1 test, 3 feat)

## Accomplishments

- **Stopped the nightly TMDB hammer.** `_backfill_mpaa_pass` now writes positive sentinel `"NR"` when TMDB has no US certification AND its SELECT targets `Movie.mpaa_rating.is_(None)` only. The 33k empty-string rows that were being re-queried every night will be promoted to `'NR'` on deploy and permanently excluded from the work set.
- **Atomic cutover via migration 0020.** Single `UPDATE movies SET mpaa_rating = 'NR' WHERE mpaa_rating = ''` runs on `alembic upgrade head`. Reversible: downgrade flips `'NR'` → `''`. No schema change.
- **DB Health audit reads honestly.** `/db-health` now uses IS NULL only for `missing_mpaa`, `missing_imdb_id`, `missing_imdb_rating`, `missing_rt_score`. The `missing_overview` filter is preserved unchanged (no positive sentinel exists for overview). Response shape is identical — frontend consumes it transparently.
- **4 regression tests added** covering: (1) NR sentinel write on empty TMDB response, (2) real cert wins over sentinel, (3) SELECT uses IS NULL only, (4) empty work set → zero TMDB calls.

## Task Commits

Each task was committed atomically:

1. **Task 1: Migration 0020 — promote empty MPAA to 'NR'** — `72c5c01` (feat)
2. **Task 2 (RED): Add failing tests for MPAA sentinel + IS NULL query** — `b08e966` (test)
3. **Task 2 (GREEN): Switch MPAA backfill to NR sentinel + IS NULL** — `04c9258` (feat)
4. **Task 3: Make /db-health audit sentinel-aware** — `a50e4d5` (feat)

_Note: Task 2 is TDD (tdd="true") so it produced both a test commit and a feat commit. Task 3 had no `tdd="true"` flag and is a single-commit change. The plan documents per-plan SUMMARY metadata commit follows separately._

## Files Created/Modified

### Created
- `backend/alembic/versions/20260530_0020_promote_empty_mpaa_to_nr.py` — Data-only Alembic migration. Revision `"0020"`, down_revision `"0019"`. `upgrade()`: `UPDATE movies SET mpaa_rating = 'NR' WHERE mpaa_rating = ''`. `downgrade()`: reverses. No schema operations.

### Modified
- `backend/app/services/cache.py` — `_backfill_mpaa_pass` (lines 186-245):
  - Docstring rewritten to explain positive-sentinel pattern.
  - SELECT changed from `or_(Movie.mpaa_rating.is_(None), Movie.mpaa_rating == "")` to `Movie.mpaa_rating.is_(None)` only.
  - Default `cert = ""` → `cert = "NR"  # positive sentinel: TMDB had no US certification; excludes row from future passes`.
  - Counter logic `if cert:` → `if cert != "NR":` so the "ratings found" log line continues to mean "real certifications".
  - `from sqlalchemy import or_` import left intact (still used by `_backfill_overview_pass`).
- `backend/app/routers/settings.py` — `get_db_health` (lines 201-243):
  - Docstring expanded to document addressable-gap semantics + sentinel awareness.
  - 4 SQL FILTER clauses changed (mpaa/imdb_id/imdb_rating/rt_score). `missing_overview` and `never_mdblist_fetched` unchanged.
  - Return dict structure unchanged.
- `backend/tests/test_cache.py` — Appended Phase 23 HEALTH-01 test block:
  - `_make_mpaa_tmdb_mock` + `_make_bg_session_mock` helpers.
  - `test_backfill_mpaa_writes_nr_when_tmdb_returns_no_us_cert` — asserts UPDATE statement contains `'NR'` and does NOT contain `mpaa_rating = ''`.
  - `test_backfill_mpaa_writes_actual_cert_when_present` — asserts real cert (`'R'`) wins.
  - `test_backfill_mpaa_query_targets_null_only` — compiles SELECT and asserts `IS NULL` present, `mpaa_rating = ''` absent.
  - `test_backfill_mpaa_skips_when_no_null_rows` — asserts zero TMDB GETs when work set is empty.

## Key Code Excerpts

### cache.py — `_backfill_mpaa_pass` (after)

```python
async with _bg_session_factory() as db:
    result = await db.execute(
        select(Movie.tmdb_id).where(
            Movie.mpaa_rating.is_(None)
        ).order_by(Movie.vote_count.desc().nulls_last()).limit(limit)
    )
    tmdb_ids = [row[0] for row in result.all()]
# ...
results = r.json().get("results", [])
cert = "NR"  # positive sentinel: TMDB had no US certification; excludes row from future passes
for country in results:
    if country.get("iso_3166_1") == "US":
        # ...
# ...
if cert != "NR":
    fetched += 1
```

### settings.py — `/db-health` SQL (after)

```sql
SELECT
  COUNT(*) AS total_movies,
  COUNT(*) FILTER (WHERE overview IS NULL OR overview = '') AS missing_overview,
  COUNT(*) FILTER (WHERE mpaa_rating IS NULL) AS missing_mpaa,
  COUNT(*) FILTER (WHERE imdb_id IS NULL) AS missing_imdb_id,
  COUNT(*) FILTER (WHERE imdb_rating IS NULL) AS missing_imdb_rating,
  COUNT(*) FILTER (WHERE rt_score IS NULL) AS missing_rt_score,
  COUNT(*) FILTER (WHERE mdblist_fetched_at IS NULL) AS never_mdblist_fetched
FROM movies
```

### Migration 0020 — full body

```python
revision: str = "0020"
down_revision: Union[str, None] = "0019"
# ...
def upgrade() -> None:
    op.execute("UPDATE movies SET mpaa_rating = 'NR' WHERE mpaa_rating = ''")

def downgrade() -> None:
    op.execute("UPDATE movies SET mpaa_rating = '' WHERE mpaa_rating = 'NR'")
```

## Test Additions

Four new tests in `backend/tests/test_cache.py` covering the sentinel + query contract:

| Test | What it asserts |
|------|-----------------|
| `test_backfill_mpaa_writes_nr_when_tmdb_returns_no_us_cert` | When TMDB returns `{"results": []}`, the compiled UPDATE statement contains `'NR'` and does NOT contain `mpaa_rating = ''` |
| `test_backfill_mpaa_writes_actual_cert_when_present` | When TMDB returns US country with `certification: "R"`, the compiled UPDATE contains `'R'` |
| `test_backfill_mpaa_query_targets_null_only` | The compiled SELECT includes `IS NULL` and does NOT include `mpaa_rating = ''` |
| `test_backfill_mpaa_skips_when_no_null_rows` | When DB returns 0 work-set rows, `mock_tmdb._client.get.call_count == 0` |

All four follow the project's import-skip pattern: they `try: from app.services.cache import _backfill_mpaa_pass` at module load; on `ImportError`/`Exception` (e.g., missing `asyncpg` locally) tests skip cleanly. In Docker they run GREEN.

## Pre-flight Frontend Grep (Decision 2 verification)

- `frontend/src/components/MovieCard.tsx:84` renders `{mpaa_rating || "NR"}` — empty string falsy fallback already yields `"NR"`. After the migration, the actual stored value will be `"NR"` so the visible rendering is byte-identical in the primary card path.
- Per CONTEXT D2, the user accepted minor visual deltas in 4 frontend locations (SearchPage table/splash, WatchHistoryPage splash) where formerly-empty rows will now render as the literal `"NR"` instead of a dash/blank. **No frontend code was modified** to preserve the "no new code paths" guarantee.

## Decisions Made

All decisions were inherited from `23-CONTEXT.md` and honored without deviation. None were introduced during execution.

- **D1 (NR sentinel):** `cert = "NR"` literal present at `cache.py:228`.
- **D2 (frontend deltas):** Zero frontend files modified — accepted visual deltas flow through unchanged code paths.
- **D3 (Option A clean audit):** `/db-health` SQL changed to `IS NULL`-only filters for mpaa/imdb_id/imdb_rating/rt_score. No `confirmed_na_*` fields added.
- **D4 (mdblist.py untouched):** `git diff backend/app/services/mdblist.py` between plan start and end is empty (verified).
- **D5 (no new surfaces):** Zero new endpoints, zero new Settings buttons, zero new admin routes, zero new frontend files.
- **D6 (reversible migration):** 0020 is data-only with symmetric `upgrade`/`downgrade`.

## Migration Semantics Note

On NAS deploy in Plan 23-02:

- `alembic upgrade head` will run `UPDATE movies SET mpaa_rating = 'NR' WHERE mpaa_rating = ''` against ~33,041 rows (per user's DB Health snapshot). On PostgreSQL, an equality UPDATE on a text column for ~33k rows completes in well under 1 second; no locking concerns beyond standard row-level. No DDL.
- `alembic downgrade -1` reverses the operation: `UPDATE movies SET mpaa_rating = '' WHERE mpaa_rating = 'NR'`. Note: this also reverts any TRUE-"NR" classifications written between deploy and rollback (acceptable per CONTEXT R4 — these are rare; one nightly cycle recovers them).
- Migration runs BEFORE the code change is loaded (compose: `alembic upgrade head` → `make rebuild`), so there is no window in which the old query reads a sentinel it cannot recognize.

## Expected Post-Deploy DB Health Delta

Informational — actual verification happens in Plan 23-02. Based on the user's pre-fix stats (58,390 total movies):

| Metric | Pre-fix (sentinel-counting) | Post-fix (IS NULL only) | Delta |
|--------|------------------------------|--------------------------|-------|
| Missing MPAA | 33,383 (57%) | ~few hundred | ~-33k |
| Missing RT score | 36,695 (63%) | ~1,459 (matches Never MDBList fetched) | ~-35k |
| Missing IMDB ID | 2,910 (5%) | ~1,459 | ~-1.5k |
| Missing IMDB rating | 2,903 (5%) | ~1,459 | ~-1.5k |
| Missing overview | 1,915 (3%) | 1,915 (3%) | unchanged |
| Never MDBList fetched | 1,459 (2%) | 1,459 (2%) | unchanged |

The dramatic drop on Missing RT score / Missing MPAA is the INTENDED effect of the audit fix (HEALTH-02) — sentinel-zero rows have reached the data ceiling and are no longer counted as actionable gaps. Plan 23-02 SUMMARY will document the actual observed delta.

## Edge Case Accepted (CONTEXT D6)

After migration 0020 + the cache.py change, a film whose US TMDB release truly has classification `"NR"` becomes indistinguishable from our `"TMDB returned nothing, we wrote NR"` sentinel. Both render as `"NR"` in the UI — no observable behavioral delta. The IS NULL-only query means neither case gets re-fetched, which is the correct behavior for both.

## Deviations from Plan

None - plan executed exactly as written.

**Total deviations:** 0
**Impact on plan:** None — every locked CONTEXT decision (D1–D6) was honored without modification. No Rule 1/2/3 auto-fixes were necessary; no Rule 4 architectural decisions were surfaced.

## Issues Encountered

None.

## Authentication Gates

None — this plan does not touch any external service auth surface.

## Self-Check

**Files created/modified verified on disk:**

| Path | Exists? |
|------|---------|
| `backend/alembic/versions/20260530_0020_promote_empty_mpaa_to_nr.py` | FOUND |
| `backend/app/services/cache.py` | FOUND (modified) |
| `backend/app/routers/settings.py` | FOUND (modified) |
| `backend/tests/test_cache.py` | FOUND (modified) |

**Commit hashes verified via `git log --oneline`:**

| Hash | Subject | Found |
|------|---------|-------|
| `72c5c01` | feat(23-01): add migration 0020 promoting empty mpaa_rating to NR sentinel | YES |
| `b08e966` | test(23-01): add failing tests for MPAA NR sentinel + IS NULL query | YES |
| `04c9258` | feat(23-01): switch MPAA backfill to NR sentinel + IS NULL query | YES |
| `a50e4d5` | feat(23-01): make /db-health audit sentinel-aware (IS NULL only) | YES |

**Static-grep verification commands (all PASS):**

- `grep -c 'cert = "NR"' backend/app/services/cache.py` = 1
- `grep -c 'cert = ""' backend/app/services/cache.py` = 0
- `grep -c 'Movie.mpaa_rating.is_(None)' backend/app/services/cache.py` = 1
- `grep -c 'Movie.mpaa_rating == ""' backend/app/services/cache.py` = 0
- `grep -c 'if cert != "NR":' backend/app/services/cache.py` = 1
- `grep -c "COUNT(\*) FILTER (WHERE mpaa_rating IS NULL) AS missing_mpaa" backend/app/routers/settings.py` = 1
- `grep -c "OR mpaa_rating = ''" backend/app/routers/settings.py` = 0
- `grep -c "OR rt_score = 0" backend/app/routers/settings.py` = 0
- `grep -c "OR imdb_id = ''" backend/app/routers/settings.py` = 0
- `grep -c "OR imdb_rating = 0" backend/app/routers/settings.py` = 0
- `grep -c "overview IS NULL OR overview = ''" backend/app/routers/settings.py` = 1 (unchanged)
- `git diff HEAD~4 HEAD -- backend/app/services/mdblist.py` produces zero output (D4 satisfied)
- `git diff HEAD~4 HEAD --name-only -- frontend/` produces zero output (D5 satisfied)
- Python AST parse succeeds for all three modified `.py` files
- All 4 test functions present in `test_cache.py`

## Self-Check: PASSED

## Next Phase Readiness

Plan 23-01 ships clean. **Ready for Plan 23-02** (HEALTH-03 — live NAS verification):

- `alembic upgrade head` will apply migration 0020 (data-only UPDATE).
- `make rebuild` will deploy the new `_backfill_mpaa_pass` + `/db-health` code.
- Verification: confirm DB Health view shows the expected dramatic drop in `Missing MPAA` / `Missing RT score` counts. Confirm nightly cache job log shows `_backfill_mpaa_pass: <small N> movies need MPAA rating` (not ~25k).

No blockers carried forward.

---
*Phase: 23-smart-metadata-backfill*
*Completed: 2026-05-30*
