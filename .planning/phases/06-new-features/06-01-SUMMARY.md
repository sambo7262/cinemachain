---
phase: 06-new-features
plan: 01
subsystem: database
tags: [postgres, sqlalchemy, alembic, fernet, encryption, fastapi, settings]

# Dependency graph
requires:
  - phase: 05-production-deployment
    provides: working Docker deployment with PostgreSQL and Alembic migrations
provides:
  - AppSettings ORM model with key/value/is_secret/updated_at columns
  - Movie.overview column (Text, nullable) in ORM and via Alembic migration 0007
  - Alembic migration 0007 creating app_settings table and adding overview column
  - settings_service.py with Fernet encrypt/decrypt, CRUD, and .env migration
  - GET /api/settings, PUT /api/settings, GET /api/settings/status endpoints
  - .env-to-DB settings migration on first startup when app_settings table is empty
affects: [06-02, 06-03, 06-04, 06-05, 06-06, 06-07, 06-08]

# Tech tracking
tech-stack:
  added: [cryptography>=42.0 (Fernet symmetric encryption)]
  patterns:
    - Upsert via select-then-merge pattern (no native upsert for portability)
    - Secret detection by keyword presence in key name ("key", "token", "password")
    - Fernet encryption optional — graceful plaintext fallback when key not configured
    - .env migration guard: only runs when app_settings table is empty

key-files:
  created:
    - backend/app/services/settings_service.py
    - backend/app/routers/settings.py
    - backend/alembic/versions/20260322_0007_overview_app_settings.py
  modified:
    - backend/app/models/__init__.py
    - backend/app/main.py
    - backend/app/settings.py
    - backend/requirements.txt
    - backend/.env.example

key-decisions:
  - "Fernet encryption is optional: if SETTINGS_ENCRYPTION_KEY is empty, secrets stored as plaintext — allows deployment without key initially"
  - "Secret detection by keyword in key name (key, token, password) rather than an explicit list — extensible without code changes"
  - "Upsert via select + conditional add/update rather than DB-level upsert — avoids dialect-specific SQL"
  - "Import from app.db not app.database — matches existing project convention"

patterns-established:
  - "Settings router: prefix on router class, not on include_router, to avoid double-prefix"
  - "AsyncSessionLocal() used directly in lifespan for startup tasks outside request scope"

requirements-completed: [ITEM-6]

# Metrics
duration: 2min
completed: 2026-03-22
---

# Phase 6 Plan 01: Settings Infrastructure Summary

**AppSettings DB model + Fernet-encrypted settings API (GET/PUT /api/settings) + Alembic migration 0007 adding Movie.overview and app_settings table**

## Performance

- **Duration:** ~2 min
- **Started:** 2026-03-22T14:28:07Z
- **Completed:** 2026-03-22T14:30:01Z
- **Tasks:** 2
- **Files modified:** 7 (3 created, 4 modified)

## Accomplishments
- AppSettings ORM model and Movie.overview column added to models/__init__.py
- Alembic migration 0007 creates app_settings table and adds overview column (down_revision = "0006")
- settings_service.py: encrypt_value/decrypt_value via Fernet, get/save/migrate_env functions
- Settings REST API: GET /api/settings, PUT /api/settings, GET /api/settings/status
- .env settings automatically migrated to DB on first startup (no-op if already populated)

## Task Commits

Each task was committed atomically:

1. **Task 1: Alembic migration + AppSettings model + Movie.overview column** - `d5af328` (feat)
2. **Task 2: Settings service with Fernet encryption + settings router + .env migration** - `4762f1f` (feat)

## Files Created/Modified
- `backend/app/models/__init__.py` - Added Movie.overview column and AppSettings model
- `backend/alembic/versions/20260322_0007_overview_app_settings.py` - Migration: app_settings table + overview column
- `backend/app/services/settings_service.py` - Fernet encryption, CRUD, .env migration
- `backend/app/routers/settings.py` - GET/PUT /settings, GET /settings/status endpoints
- `backend/app/main.py` - Mounted settings router, added migrate_env_to_db startup call
- `backend/app/settings.py` - Added settings_encryption_key optional field
- `backend/requirements.txt` - Added cryptography>=42.0
- `backend/.env.example` - Added SETTINGS_ENCRYPTION_KEY with generation instructions

## Decisions Made
- Fernet encryption is optional (empty key = plaintext storage) to simplify initial deployment
- Secret detection by keyword match in key name — avoids hardcoded allowlist
- Upsert implemented as select-then-add/update for SQLAlchemy portability
- Corrected plan's `app.database` import reference to actual `app.db` module

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Corrected import path from app.database to app.db**
- **Found during:** Task 2 (settings router implementation)
- **Issue:** Plan specified `from app.database import get_db` but project uses `app.db` module
- **Fix:** Used `from app.db import get_db` matching existing router pattern
- **Files modified:** backend/app/routers/settings.py
- **Verification:** Checked health.py which uses `from app.db import get_db`
- **Committed in:** 4762f1f (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (1 blocking import path correction)
**Impact on plan:** Required correction — plan had incorrect module name. No scope creep.

## Issues Encountered
- Local `asyncpg` not installed, preventing runtime import verification. Verified syntax via `ast.parse()` and confirmed all acceptance criteria with grep. App runs in Docker where all deps are installed.

## User Setup Required
None - no external service configuration required beyond optional SETTINGS_ENCRYPTION_KEY.

## Next Phase Readiness
- AppSettings table and Movie.overview column ready for Alembic migration run
- Settings API ready for frontend consumption (Phase 6 plans 02+)
- migrate_env_to_db will auto-populate settings on first startup
- Blocker for Item 2 (movie splash/overview) unblocked: overview column exists

---
*Phase: 06-new-features*
*Completed: 2026-03-22*
