# Deferred Items — Phase 03 Movie Game

## Pre-existing Issues (Out of Scope)

### test_models.py fails on system Python 3.9
- **Found during:** Task 2 verification (03-05)
- **Issue:** `test_models.py::test_all_four_tables_registered` fails with `TypeError: unsupported operand type(s) for |: 'type' and 'NoneType'` because system Python 3.9 does not support `int | None` union type syntax in class bodies at definition time.
- **Root cause:** Pre-existing — all ORM models use `Mapped[int | None]` (Python 3.10+ syntax). Project targets Python 3.12 via Docker; system Python 3.9 cannot run these tests.
- **Fix path:** Add `from __future__ import annotations` to `backend/app/models/__init__.py` to defer annotation evaluation. OR test via Docker only.
- **Not fixed because:** Out of scope — pre-existing issue not caused by 03-05 changes. The project's Docker environment (Python 3.12) handles this correctly.
