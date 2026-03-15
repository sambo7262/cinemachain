---
phase: 03-movie-game
plan: "02"
subsystem: database
tags: [sqlalchemy, alembic, postgresql, orm, game-session]

# Dependency graph
requires:
  - phase: 03-01
    provides: Phase 3 context, game design, research decisions
  - phase: 02-01
    provides: Base ORM models (Movie, Actor, Credit, WatchEvent) and initial Alembic migration pattern
provides:
  - GameSession and GameSessionStep ORM models with lazy="raise" relationships
  - SessionStatus enum (active, paused, awaiting_continue, ended) stored as String(20)
  - runtime column on Movie model (nullable Integer)
  - Alembic migration 0002 chained from 20260315_0001, creating game_sessions and game_session_steps tables
affects: [03-03, 03-04, 03-05, 03-06, game-api, game-service]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - SessionStatus as Python str enum stored as plain String(20) — avoids PostgreSQL ENUM migration complexity
    - lazy="raise" on all ORM relationships — async SQLAlchemy cannot lazy-load; callers must use selectinload()
    - Hand-authored Alembic migration with explicit PrimaryKeyConstraint and ForeignKeyConstraint — no live DB at plan time
    - game_session_steps FK index created explicitly (ix_game_session_steps_session_id) for query performance

key-files:
  created:
    - backend/alembic/versions/20260315_0002_game_session_schema.py
  modified:
    - backend/app/models/__init__.py

key-decisions:
  - "SessionStatus stored as String(20) not PostgreSQL ENUM — avoids Alembic complexity with enum migrations; Python enum used for type safety in application code only"
  - "GameSession.current_movie_tmdb_id is non-nullable Integer — the starting movie is required at session creation time"
  - "GameSessionStep.actor_tmdb_id and actor_name are nullable — first step (starting movie) has no actor transition"
  - "Migration 0002 uses explicit PrimaryKeyConstraint/ForeignKeyConstraint pattern from 0001, not inline column constraints — consistent style"

patterns-established:
  - "Pattern: Hand-authored migrations with explicit constraint objects (sa.PrimaryKeyConstraint, sa.ForeignKeyConstraint) not inline column args"
  - "Pattern: All game tables created with nullable=False DateTime columns (created_at, updated_at) — defaults handled by ORM not DB"

requirements-completed: [GAME-01, GAME-04]

# Metrics
duration: 3min
completed: 2026-03-15
---

# Phase 3 Plan 02: Game Session Schema Summary

**SQLAlchemy ORM extended with GameSession/GameSessionStep models and hand-authored Alembic migration 0002 adding game_sessions, game_session_steps tables and runtime column on movies**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-15T16:52:42Z
- **Completed:** 2026-03-15T16:55:42Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments

- Extended `backend/app/models/__init__.py` with `SessionStatus` enum, `GameSession`, and `GameSessionStep` ORM models following Phase 2 lazy="raise" pattern
- Added `runtime: Mapped[int | None]` field to Movie model to support runtime-based game display
- Created hand-authored Alembic migration `0002` chained from `20260315_0001`, creating both game tables with proper FK/index structure and runtime column on movies

## Task Commits

Each task was committed atomically:

1. **Task 1: Extend ORM models with GameSession, GameSessionStep, and runtime field** - `e85e876` (feat)
2. **Task 2: Hand-author Alembic migration for game schema** - `231ba12` (feat)

**Plan metadata:** (to be filled by final commit)

## Files Created/Modified

- `backend/app/models/__init__.py` - Added `import enum`, `runtime` field on Movie, `SessionStatus` enum, `GameSession` model, `GameSessionStep` model
- `backend/alembic/versions/20260315_0002_game_session_schema.py` - Alembic migration adding runtime column and creating game_sessions/game_session_steps tables

## Decisions Made

- SessionStatus is a Python `str` enum stored as `String(20)` in the database — no PostgreSQL ENUM type used, avoiding Alembic migration complexity for enum alterations.
- `GameSessionStep.actor_tmdb_id`, `actor_name`, and `movie_title` are nullable — the first step in a session represents the starting movie with no actor transition.
- Migration uses the same explicit constraint style (`sa.PrimaryKeyConstraint`, `sa.ForeignKeyConstraint`) as the 0001 migration rather than inline column args.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

- System Python (3.9.6) is too old for `int | None` union syntax used in models — verified with Docker Python 3.12 image instead. The project uses Python 3.12 in Dockerfile and this is the correct runtime; no fix needed.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- GameSession and GameSessionStep ORM models are ready for service layer implementation (Phase 3 Plan 03+)
- Migration 0002 will be applied on next `alembic upgrade head` run against the PostgreSQL database
- All new relationships use lazy="raise" — callers in game service must use `selectinload(GameSession.steps)` pattern

## Self-Check: PASSED

- FOUND: backend/app/models/__init__.py
- FOUND: backend/alembic/versions/20260315_0002_game_session_schema.py
- FOUND: .planning/phases/03-movie-game/03-02-SUMMARY.md
- FOUND: commit e85e876 (Task 1)
- FOUND: commit 231ba12 (Task 2)

---
*Phase: 03-movie-game*
*Completed: 2026-03-15*
