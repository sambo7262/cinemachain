# Phase 23 Context: Smart Metadata Backfill (v2.0.2 patch)

**Phase goal:** Stop wasteful nightly TMDB/MDBList re-queries against movies where the data ceiling has been reached, AND fix the DB Health audit to report the actually-addressable gap (not sentinel-zero false positives). Net effect: `Missing MPAA` and `Missing RT score` stats drop from ~30k each to a few hundred genuinely addressable rows that close within 1-2 nightly cycles.

**Requirements:** HEALTH-01 (MPAA sentinel + query fix), HEALTH-02 (DB Health audit accuracy), HEALTH-03 (live NAS verification)

**Patch lineage:** v2.0.2 (post-v2.0 patch; not v2.1 — substantive new features wait for v2.1).

---

## Origin — user-reported data quality stats (2026-05-29)

User's DB Health view showed:

| Metric | Count / % |
|--------|-----------|
| Total movies | 58,390 |
| Missing overview | 1,915 (3%) |
| **Missing MPAA** | **33,383 (57%)** |
| Missing IMDB ID | 2,910 (5%) |
| Missing IMDB rating | 2,903 (5%) |
| **Missing RT score** | **36,695 (63%)** |
| Never MDBList fetched | 1,459 (2%) |

User's intent: "take the existing jobs and target the data gaps better" — auto-only, no new UI/buttons. **The fix shouldn't just be cosmetic (audit query) but should actually stop the wasteful nightly TMDB/MDBList calls.**

---

## Investigation — what the existing code actually does

### MDBList side (services/mdblist.py) — already correct

The MDBList code **already implements the positive-sentinel pattern**. On 404 (movie not in MDBList) at line 87-97 it writes:
- `rt_score = 0`
- `imdb_rating = 0.0`
- `imdb_id = ""`
- `metacritic_score = 0`
- `letterboxd_score = 0.0`
- `mdb_avg_score = 0.0`
- `mdblist_fetched_at = NOW()`

On 200-but-empty at line 130-139, same sentinels written, same `mdblist_fetched_at` stamp.

The query at line 60 + line 229 (`backfill_mdblist_scores`):
```python
or_(Movie.rt_score.is_(None), Movie.imdb_rating.is_(None))
```

This correctly skips sentinel-0 rows. **No bug here.**

### MPAA side (services/cache.py) — has the bug

`_backfill_mpaa_pass` at line 186 uses:
```python
or_(Movie.mpaa_rating.is_(None), Movie.mpaa_rating == "")
```

And on empty response at line 224-238 writes:
```python
cert = ""  # empty string when TMDB has no US certification
...
.values(mpaa_rating=cert)
```

**The bug:** empty string is both the "store nothing" output AND the "re-query me" input. So every night, ~25k movies (the `limit=25000` cap) get re-fetched from TMDB with no result, write `""` again, and the cycle repeats.

The header comment at line 188 even acknowledges this: "Retries empty-string sentinel so previously-failed lookups get another chance." — but in practice TMDB doesn't suddenly start having US certifications for international/older films, so this is wasteful.

### Why the user sees 36,695 missing RT but only 1,459 never-fetched

Because the DB Health audit endpoint **counts sentinel-zeros as "missing"**. The real breakdown is approximately:

| Bucket | Estimate | Description |
|--------|----------|-------------|
| Truly never MDBList-fetched | ~1,459 | `mdblist_fetched_at IS NULL` |
| MDBList-fetched, RT confirmed N/A | ~35,236 | `rt_score = 0`, `mdblist_fetched_at IS NOT NULL` |

Same shape for IMDB ID, IMDB rating, etc. The MDBList sentinel pattern works correctly at the data layer — the **audit query is the bug**.

### Why the user sees 33,383 missing MPAA

Pure addressable count is unknown without the fix, but likely breaks down:
- A small set TMDB simply never returned data for (legitimately empty)
- Plus ~25k re-tried-every-night-forever movies that ARE the empty-string sentinel

After Phase 23 ships, the migration promotes all current `""` to `"NR"`, and the new query targets only `IS NULL`. The "addressable" gap should be near-zero (= movies that have NEVER been processed by `_backfill_mpaa_pass`, which should be a small set because the pass runs nightly against the whole `mpaa IS NULL` set with a 25k cap).

---

## Decision 1 — MPAA: positive sentinel `"NR"`

**Decision:** When `_backfill_mpaa_pass` finds no US certification, store `mpaa_rating = "NR"` instead of `""`. Update the query to target `mpaa_rating IS NULL` only.

**Why "NR"?**
- It's the conventional "Not Rated" classification — semantically truthful when TMDB has no US cert
- Phase 8 already established "explicit N/A" rendering for movies with no MPAA data — Frontend should treat `"NR"` the same as it currently treats `""`
- It's a positive value (not empty) so the database query naturally excludes it from the "needs work" set

**One-time data fix — migration 0020:**
```sql
UPDATE movies SET mpaa_rating = 'NR' WHERE mpaa_rating = '';
```
Promotes all existing 33k `""` rows to `"NR"`. Immediately stops the nightly retry waste on deploy.

**Why NOT add a `mpaa_fetched_at` column?** Considered. Rejected because:
- The positive-sentinel pattern is already in use across the codebase (MDBList side does this for RT/IMDB)
- Migration is simpler (UPDATE vs ALTER TABLE + UPDATE)
- No new schema state to reason about

---

## Decision 2 — Frontend MPAA rendering check

**Decision:** Verify frontend handles `"NR"` identically to current `""` rendering before deploying the migration. If the frontend currently shows nothing for `""` but would show "NR" badge for `"NR"`, that's a UI change.

**Pre-flight check during plan execution:**
```bash
grep -rn 'mpaa_rating\b' frontend/src/ | head -20
```

Likely the frontend already handles `"NR"` correctly (per Phase 8 decision about explicit N/A) — but verify before assuming. If there's a UI delta, decide whether to:
1. Accept the visual change (NR badge replaces blank — probably more honest anyway)
2. Frontend-side translate `"NR"` to blank for backward compat (preserves old UI)

User mentioned no regression is acceptable. Option 1 is fine if the badge is sane; Option 2 if the badge surfaces aesthetically wrong.

---

## Decision 3 — DB Health audit: "addressable" vs "confirmed N/A" semantics

**Decision:** Update the DB Health audit endpoint (added in Phase 17 per ROADMAP) to distinguish "addressable gap" (truly NULL — still actionable) from "confirmed N/A" (sentinel — data ceiling reached).

**Proposed dashboard format (Option A — clean):**
```
Missing overview:    1,915 (3% — addressable)
Missing MPAA:           342 (0.6% — addressable)
Missing IMDB ID:      1,459 (3% — addressable)
Missing IMDB rating:  1,459 (3% — addressable)
Missing RT score:     1,459 (3% — addressable)
Never MDBList fetched: 1,459 (2% — addressable)
```

**Proposed dashboard format (Option B — full transparency):**
```
| Metric | Addressable (NULL) | Confirmed N/A (sentinel) |
|---|---|---|
| MPAA | 342 | 33,041 |
| RT score | 1,459 | 35,236 |
| IMDB ID | 1,459 | ~1,400 |
```

**Default to Option A** unless the user explicitly wants the breakdown (the "confirmed N/A" count is mostly noise — it's the data ceiling). If Option B is wanted, planner can adjust.

**Query semantics per metric:**
| Stat | Old query (counts sentinels) | New query (NULL only) |
|------|-------------------------------|-----------------------|
| Missing overview | `WHERE overview IS NULL` | unchanged — no sentinel exists |
| Missing MPAA | `WHERE mpaa_rating IS NULL OR mpaa_rating = ''` | `WHERE mpaa_rating IS NULL` |
| Missing IMDB ID | `WHERE imdb_id IS NULL OR imdb_id = ''` | `WHERE imdb_id IS NULL` |
| Missing IMDB rating | `WHERE imdb_rating IS NULL OR imdb_rating = 0` | `WHERE imdb_rating IS NULL` |
| Missing RT score | `WHERE rt_score IS NULL OR rt_score = 0` | `WHERE rt_score IS NULL` |
| Never MDBList fetched | `WHERE mdblist_fetched_at IS NULL` | unchanged |

**Note on RT/IMDB sentinels:** since MDBList code writes `0` / `""` AND stamps `mdblist_fetched_at = NOW()` together, "Missing RT score" using `rt_score IS NULL` should equal "Never MDBList fetched" using `mdblist_fetched_at IS NULL` (both = 1,459 in the user's stats). Worth verifying the math during implementation.

---

## Decision 4 — Scope: MPAA + audit only; do NOT touch MDBList code

**Decision:** Phase 23 modifies `_backfill_mpaa_pass` (MPAA backfill — has the bug) and the DB Health audit endpoint (visibility bug). It does NOT modify any MDBList code (services/mdblist.py is already correct).

**Why scope discipline:** the user said "we have the right jobs" — they don't want speculative refactoring of the working MDBList code. Confine changes to what's actually wrong.

---

## Decision 5 — Auto-only, no new buttons or UI triggers

**Decision:** Phase 23 does NOT add any new Settings button, manual trigger, or admin endpoint. The fix is entirely:
1. Sentinel pattern change in existing backfill code (silent — runs on nightly schedule)
2. Migration 0020 (one-time, applies on `alembic upgrade head`)
3. Audit query semantics in existing DB Health endpoint (silent — drives existing UI)

**Why:** user said "id just want any work here to take the existing jobs and target the data gaps better" — auto-only. The existing nightly + DB Health view already provides the necessary feedback loop.

---

## Decision 6 — Migration safety

**Decision:** Migration 0020 is purely additive in semantic effect — it changes data values but not schema. Downgrade path: revert `'NR'` → `''` (preserves rollback symmetry).

```python
# upgrade()
op.execute("UPDATE movies SET mpaa_rating = 'NR' WHERE mpaa_rating = ''")

# downgrade()
op.execute("UPDATE movies SET mpaa_rating = '' WHERE mpaa_rating = 'NR'")
```

**Edge case:** what if a future TMDB response legitimately returns `"NR"` as the certification (some films are explicitly rated NR)? After the migration, we can't distinguish "TMDB returned NR" from "TMDB returned empty, we wrote NR ourselves". This is acceptable because both render as N/A to the user — no observable behavioural difference.

---

## Regression risk register

| Risk | Mitigation |
|------|------------|
| Frontend renders `"NR"` differently than `""` | Pre-flight grep confirms Phase 8 "explicit N/A" handling already covers both |
| Audit query change shows different counts on first load | This IS the desired effect — counts should drop dramatically. Document in SUMMARY |
| Future TMDB returns true `"NR"` certification mixed with our sentinel | Acceptable — both render as N/A |
| Migration takes a long time on 58k rows | UPDATE with index on mpaa_rating completes in <1s on PostgreSQL; no concern |
| Existing 25k/night cap is no longer needed | Lower it to e.g. 5,000 to free up TMDB budget for actor filmography refresh; or leave as-is |

---

## Out of scope (deferred)

- New endpoints, Settings buttons, manual triggers — Decision 5
- Refactoring MDBList code (already correct) — Decision 4
- Adding `mpaa_fetched_at` timestamp column (chose simpler sentinel pattern) — Decision 1
- v2.1 backlog items (Plex polling, stats dashboard, etc.)

---

## Implementation hints for planner

- MPAA backfill: `backend/app/services/cache.py:186-245` — change `cert = "NR"` default, update `or_(...)` query to `mpaa_rating.is_(None)` only
- Migration: `backend/alembic/versions/20260530_0020_promote_empty_mpaa_to_nr.py`; down_revision = "0019"
- DB Health endpoint: Phase 17 — likely lives in `backend/app/routers/cache.py` or a new `routers/admin.py`. Need to grep for the endpoint and its query implementation.
- Frontend rendering check: `frontend/src/components/RatingsBadge.tsx` and `MovieCard.tsx` likely consumers of `mpaa_rating`
- Tests: `backend/tests/test_cache.py` — add cases for sentinel pattern (empty → NR + query skips NR)
- Verification: `docker logs backend | grep _backfill_mpaa_pass` post-deploy should show small "ratings found" counts (not 25k)
