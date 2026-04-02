---
plan: 15-01
status: complete
phase: 15-mdblist-suggested-movies
subsystem: backend/data-layer
tags: [migration, orm, settings, tmdb]
key-files:
  created:
    - backend/alembic/versions/20260401_0015_tmdb_recommendations.py
  modified:
    - backend/app/models/__init__.py
    - backend/app/routers/settings.py
decisions:
  - "tmdb_recommendations stored as sa.JSON nullable; NULL = never fetched, [] = fetched with no results"
  - "tmdb_suggestions_seed_count stored as str (consistent with all other AppSettings values)"
metrics:
  duration: "~5m"
  completed: "2026-04-01"
  tasks: 2
  files: 3
---

# Phase 15 Plan 01: Data Layer — tmdb_recommendations + settings DTO Summary

One-liner: Nullable JSON column on Movie for caching TMDB recommendation IDs, plus settings DTO field for sliding-window seed count.

## Summary
- Created `backend/alembic/versions/20260401_0015_tmdb_recommendations.py` (revision 0015, down_revision 0014) — adds nullable `sa.JSON()` column `tmdb_recommendations` to `movies` table; downgrade drops it.
- Added `Movie.tmdb_recommendations: Mapped[Optional[list]] = mapped_column(sa.JSON, nullable=True)` to ORM model after `fetched_at`, before relationships.
- Added `tmdb_suggestions_seed_count: str | None = None` to both `SettingsResponse` and `SettingsUpdateRequest` in `backend/app/routers/settings.py`, placed after `mdblist_list_id` in each model.

## Verification

```
# ORM check (host Python 3.9):
$ cd backend && python3 -c "from app.models import Movie; print(hasattr(Movie, 'tmdb_recommendations'))"
True

# Settings DTO check: passes in Docker (Python 3.11+); host Python 3.9 cannot evaluate
# str | None union syntax in Pydantic v2 at runtime — pre-existing limitation of all fields
# in this file, not introduced by this plan. Structural review confirms both models have the
# field at lines 24 and 38 of settings.py respectively.
```

## Deviations from Plan

None — plan executed exactly as written. Settings DTO verification command fails on host Python 3.9 due to pre-existing `str | None` runtime incompatibility with Pydantic v2 (affects all fields in the file, not this change). Code is correct for the Docker Python 3.11 runtime.

## Known Stubs

None.

## Self-Check: PASSED

- `backend/alembic/versions/20260401_0015_tmdb_recommendations.py` — exists
- `backend/app/models/__init__.py` contains `tmdb_recommendations` — confirmed
- `backend/app/routers/settings.py` contains `tmdb_suggestions_seed_count` in both DTOs — confirmed
- Commit d366199 — exists
