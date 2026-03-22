---
phase: 06-new-features
verified: 2026-03-22T00:00:00Z
status: human_needed
score: 8/9 must-haves verified (1 needs human confirmation)
human_verification:
  - test: "Open an active game session and look at the Now Playing tile before selecting any actor"
    expected: "MPAA rating, runtime (Xh Ym format), and TMDB rating appear below the current movie title"
    why_human: "Now Playing stats source from allEligibleMovies.find(m => m.tmdb_id === session.current_movie_tmdb_id). If the current movie is not present in the eligible movies list (e.g., because no actor is selected yet or the combined view hasn't loaded it), the stats return null and render nothing. Cannot verify programmatically without a live session."
---

# Phase 6: New Features Verification Report

**Phase Goal:** Deliver 9 new features (Items 1-9) as a cohesive user experience upgrade — Settings/Onboarding, movie selection UX, RT ratings (decision deferred to backlog), session management, chain history search, TMDB links, and info density improvements.
**Verified:** 2026-03-22
**Status:** human_needed
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths (from ROADMAP Success Criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | CSV-imported sessions display resolved actor names (not raw TMDB IDs) | VERIFIED | `game.py:806-812` — after CSV step creation, if `step.actor_tmdb_id` is set and `step.actor_name` is None, `tmdb.fetch_person()` is called and name applied before DB commit |
| 2 | Movie selection uses a rich splash dialog with poster, overview, ratings, and optional Radarr checkbox | VERIFIED | `GameSession.tsx:1039` — Dialog with `splashOpen` state; poster at w185 TMDB URL, MPAA/rating/runtime/year badges, full overview text, TMDB link, Radarr checkbox; `handleSplashConfirm` passes `skip_radarr: !radarrChecked` |
| 3 | Session dropdown menu contains Archive Session and Edit Session Name actions | VERIFIED | `GameSession.tsx:493,499` — both menu items present; `archiveConfirmOpen` Dialog and `editNameOpen` Dialog wired to `api.archiveSession` and `api.renameSession` respectively |
| 4 | Chain history table has a working search filter for movies and actors | VERIFIED | `ChainHistory.tsx:7,17-22` — `searchQuery` state, `filteredSteps` filters on `movie_title` and actor name; placeholder "Search movies and actors…"; empty state at line 135 |
| 5 | Movies and actors have TMDB external link icons in eligible movies table and chain history | VERIFIED | Eligible movies table: `GameSession.tsx:976` (movie links). Chain history: `ChainHistory.tsx:76` (movies) + line 116 (actors via `themoviedb.org/person/{id}`). Splash dialog: `GameSession.tsx:1100`. D-20 (no links on Eligible Actors grid) intentional design decision. |
| 6 | Settings page at /settings allows configuring all service credentials, with blocking onboarding when TMDB is absent | VERIFIED | `Settings.tsx` exists with 5 Card sections, `getSettings`/`saveSettings` wired. `OnboardingScreen.tsx` renders "Welcome to CinemaChain" when `tmdb_configured=false`. `App.tsx:25-26` — `settingsStatus` query gates the whole app before any route renders. NavBar has Settings icon link at `/settings`. |
| 7 | RT ratings research findings presented to user for decision | VERIFIED | `06-07-SUMMARY.md` documents MDBList API selected; implementation deferred to post-Phase-6 backlog. Decision gate task completed in Plan 07. The success criterion is "findings presented for decision" — this is satisfied. |
| 8 | Session cards show watched count, total runtime, and started date | VERIFIED | `GameLobby.tsx:232` — `{session.watched_count} watched · {formatRuntime(session.watched_runtime_minutes)} · Started {formatDate(session.created_at)}`. Backend provides `watched_count` and `watched_runtime_minutes` in `GameSessionResponse` (game.py:50-51, 292-293). |
| 9 | Now Playing tile shows MPAA rating, runtime, and TMDB rating | ? UNCERTAIN | `GameSession.tsx:583-596` — stats render from `allEligibleMovies.find(m => m.tmdb_id === session.current_movie_tmdb_id)`. If current movie is not in the accumulated eligible movies list, returns null (no stats shown). Needs human verification that the current movie appears in combined-view results. |

**Score:** 8/9 truths verified (1 uncertain — needs human)

---

## Required Artifacts

### Plan 00 — Wave 0 Test Stubs

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `backend/tests/test_game.py` | 4 Phase 6 stubs appended | VERIFIED | `test_csv_actor_name_resolved` (L1537), `test_eligible_movie_overview_field` (L1556), `test_request_movie_skip_radarr_field` (L1578), `test_rename_session` (L1595) all present |
| `backend/tests/test_settings.py` | 1 settings stub | VERIFIED | `test_db_overrides_env` at line 57 |
| `frontend/src/components/__tests__/ChainHistory.test.tsx` | Search filter stubs (3 tests) | VERIFIED | File exists, 3 describe/it blocks for search placeholder, filter behavior, empty state |
| `frontend/src/pages/__tests__/GameLobby.test.tsx` | Session card stats stubs (4 tests) | VERIFIED | File exists, `watched_runtime_minutes: 645` mock data present |

### Plan 01 — Settings Infrastructure

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `backend/app/models/__init__.py` | `class AppSettings` + `Movie.overview` column | VERIFIED | `AppSettings` at line 117; `overview: Mapped[Optional[str]] = mapped_column(sa.Text, nullable=True)` at line 28 |
| `backend/alembic/versions/20260322_0007_overview_app_settings.py` | Migration 0007, down_revision="0006" | VERIFIED | `revision="0007"`, `down_revision="0006"`, `op.add_column("movies", sa.Column("overview"…))`, `op.create_table("app_settings"…)` all confirmed |
| `backend/app/services/settings_service.py` | Fernet encryption + CRUD + env migration | VERIFIED | All 6 required functions present: `encrypt_value`, `decrypt_value`, `get_all_settings`, `save_settings`, `is_tmdb_configured`, `migrate_env_to_db` |
| `backend/app/routers/settings.py` | GET/PUT /settings + GET /settings/status | VERIFIED | Router prefix `/settings`; `SettingsResponse`, `SettingsStatusResponse` models; all 3 endpoints at lines 46, 53, 65 |
| `backend/app/main.py` | Settings router mount + .env migration on startup | VERIFIED | `from app.routers.settings import router as settings_router` (L18), `app.include_router(settings_router, prefix="/api")` (L101), `migrate_env_to_db(db)` in lifespan (L38) |
| `backend/requirements.txt` | `cryptography>=42.0` | VERIFIED | Line 14 confirmed |
| `backend/.env.example` | `SETTINGS_ENCRYPTION_KEY` entry | VERIFIED | Lines 29-30 confirmed |

### Plan 02 — Backend Game Endpoint Changes

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `backend/app/routers/game.py` | overview in response, skip_radarr, PATCH name, CSV actor fix | VERIFIED | `EligibleMovieResponse.overview` at L137; `skip_radarr: bool = False` at L120; `@router.patch("/sessions/{session_id}/name"…)` at L1148; `fetch_person` called at L808 for CSV actor name resolution |

### Plan 03 — Frontend Info Density

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `frontend/src/pages/GameLobby.tsx` | Session card stats (watched, runtime, started date) | VERIFIED | `formatRuntime()` at L64, `formatDate()` at L70, stats line at L232 |
| `frontend/src/pages/GameSession.tsx` | Now Playing stats + TMDB links on eligible movies | VERIFIED | `allEligibleMovies.find(...)` stat block at L583-596; ExternalLink on movies at L976 |
| `frontend/src/components/ChainHistory.tsx` | Search input + TMDB links | VERIFIED | `searchQuery` useState at L7, filter at L17-22, ExternalLink movie at L76, ExternalLink actor at L116 |
| `frontend/src/lib/api.ts` | `overview: string | null` in EligibleMovieDTO | VERIFIED | `SettingsDTO`, `SettingsStatusDTO`, `getSettings`, `saveSettings`, `getSettingsStatus` all present; `skip_radarr` in `requestMovie` at L185 |

### Plan 04 — Movie Selection Splash Dialog

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `frontend/src/pages/GameSession.tsx` | Splash dialog controlled by splashOpen | VERIFIED | `splashOpen`, `splashMovie`, `radarrChecked` states at L67-69; Dialog at L1039; `handleSplashConfirm` at L230 passes `skip_radarr: !radarrChecked` at L246 |

### Plan 05 — Session Settings Menu

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `frontend/src/pages/GameSession.tsx` | Archive confirm dialog + Edit name modal | VERIFIED | `archiveConfirmOpen` at L56, `editNameOpen` at L57; Dialog at L1249, L1276; both wired to mutations at L378 (archive), L387 (rename) |

### Plan 06 — Settings Frontend

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `frontend/src/pages/Settings.tsx` | Settings page with Card sections | VERIFIED | Uses `api.getSettings`, `api.saveSettings`; "Save Settings" button at L277 |
| `frontend/src/components/OnboardingScreen.tsx` | Blocking onboarding with "Welcome to CinemaChain" | VERIFIED | `OnboardingScreen` function at L8, "Welcome to CinemaChain" text at L42 |
| `frontend/src/App.tsx` | Onboarding gate + /settings route | VERIFIED | `settingsStatus` query at L14-16; gate at L25-26; `/settings` route at L39 |
| `frontend/src/components/NavBar.tsx` | Settings icon link | VERIFIED | `to="/settings"` at L48, `SettingsIcon` at L52 |

### Plan 07 — RT Decision Gate

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| None declared in must_haves | RT decision presented to user | VERIFIED | Decision documented in 06-07-SUMMARY.md: MDBList API selected, deferred to backlog. No code artifact required for this item. |

---

## Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `backend/app/routers/settings.py` | `backend/app/services/settings_service.py` | `from app.services import settings_service` | WIRED | Line 8; `settings_service.get_all_settings()`, `.save_settings()`, `.is_tmdb_configured()` called |
| `backend/app/main.py` | `backend/app/routers/settings.py` | `app.include_router(settings_router, prefix="/api")` | WIRED | Lines 18 + 101 |
| `backend/app/main.py` | `backend/app/services/settings_service.py` | `migrate_env_to_db` in lifespan | WIRED | Line 38 in async lifespan context |
| `backend/app/routers/game.py` | `backend/app/services/tmdb.py` | `tmdb.fetch_person` for CSV actor name | WIRED | Line 808; called when `step.actor_tmdb_id and not step.actor_name` |
| `frontend/src/App.tsx` | `api.getSettingsStatus` | `useQuery` for onboarding gate | WIRED | Lines 14-16; result used at L25 to render `OnboardingScreen` |
| `frontend/src/pages/Settings.tsx` | `api.getSettings / api.saveSettings` | `useQuery + useMutation` | WIRED | Lines 45, 60 |
| `frontend/src/pages/GameSession.tsx` | `api.requestMovie` | `handleSplashConfirm` passes `skip_radarr` | WIRED | Line 246 |
| `frontend/src/pages/GameSession.tsx` | `api.renameSession` | edit name save handler | WIRED | `renameMutation` at L387 |
| `frontend/src/pages/GameSession.tsx` | `api.archiveSession` | archive confirm handler | WIRED | `archiveMutation` at L378 |
| `frontend/src/components/ChainHistory.tsx` | search filter logic | `useState + .filter() on steps` | WIRED | `searchQuery` at L7; `filteredSteps` filter at L17-22 using `searchQuery` |

---

## Requirements Coverage

| Requirement | Source Plan(s) | Description | Status | Evidence |
|-------------|---------------|-------------|--------|---------|
| ITEM-1 | Plan 00, Plan 02 | TMDB actor name resolution fix (CSV import) | SATISFIED | `game.py:806-812` — fetch_person resolves NULL actor_name after CSV step creation |
| ITEM-2 (backend) | Plan 00, Plan 02 | overview field + skip_radarr on eligible movies/request | SATISFIED | `EligibleMovieResponse.overview` at game.py:137; `skip_radarr` at game.py:120 |
| ITEM-2 (frontend) | Plan 04 | Movie selection splash dialog | SATISFIED | Splash Dialog in GameSession.tsx at L1039 with poster, overview, ratings, Radarr checkbox |
| ITEM-3 (backend) | Plan 00, Plan 02 | PATCH /sessions/{id}/name endpoint | SATISFIED | `@router.patch("/sessions/{session_id}/name"…)` at game.py:1148 |
| ITEM-3 (frontend) | Plan 05 | Session dropdown: Edit Session Name + Archive Session | SATISFIED | Both actions in GameSession.tsx DropdownMenu with corresponding dialogs |
| ITEM-4 | Plan 00, Plan 03 | Chain history search filter | SATISFIED | `ChainHistory.tsx` has full-text search with real-time filtering |
| ITEM-5 | Plan 03 | TMDB external links on movies and actors | SATISFIED | Movies in eligible movies table (GameSession.tsx:976) + splash (L1100); both movies and actors in chain history (ChainHistory.tsx:76, 116) |
| ITEM-6 (backend) | Plan 01 | AppSettings model, Fernet encryption, GET/PUT /api/settings, .env migration | SATISFIED | Full settings infrastructure implemented and mounted |
| ITEM-6 (frontend) | Plan 06 | Settings page, OnboardingScreen, NavBar link, App gate | SATISFIED | All four components implemented and wired |
| ITEM-7 | Plan 07 | RT ratings research presented for decision | SATISFIED | MDBList API selected as preferred option; deferred to backlog |
| ITEM-8 | Plan 00, Plan 03 | Session cards show watched count, total runtime, started date | SATISFIED | GameLobby.tsx:232 renders all three stats from backend fields |
| ITEM-9 | Plan 03 | Now Playing tile shows MPAA rating, runtime, TMDB rating | ? UNCERTAIN | Implementation exists at GameSession.tsx:583-596 but depends on current movie being in allEligibleMovies; needs human verification |

**REQUIREMENTS.md note:** ITEM-1 through ITEM-9 are Phase 6 new feature items defined only in ROADMAP.md. They do not appear in REQUIREMENTS.md (which covers v1 game requirements DATA-*, GAME-*, INFRA-*). No orphaned requirement IDs found — all 9 ITEMs are claimed by one or more plans in this phase.

---

## Anti-Patterns Found

No blockers or warnings found. Scan of key modified files:
- `backend/app/services/settings_service.py` — no TODO/FIXME, no empty returns
- `backend/app/routers/settings.py` — all endpoints have real implementations
- `backend/app/routers/game.py` — skip_radarr guard is real; fetch_person exception swallowed intentionally (non-critical graceful degradation per plan decision)
- `frontend/src/pages/GameSession.tsx` — `if (!currentMovie) return null` is a graceful fallback, not a stub (the feature may just not render in all states)
- `frontend/src/components/ChainHistory.tsx` — search filter is real, not a placeholder
- `frontend/src/pages/Settings.tsx` — no hardcoded stub data; reads/writes via real API

---

## Human Verification Required

### 1. Now Playing Tile Stats (ITEM-9)

**Test:** Navigate to an active game session. Look at the Now Playing tile (the section showing the current movie being watched) before selecting any actor. Do MPAA rating, runtime, and TMDB vote average appear below the movie title?

**Expected:** Three stats appear inline: MPAA badge (e.g., "R"), runtime (e.g., "2h 19m"), TMDB rating with star icon (e.g., "8.4"). All styled as `text-xs text-muted-foreground`.

**Why human:** The stats are sourced from `allEligibleMovies.find(m => m.tmdb_id === session.current_movie_tmdb_id)`. The `allEligibleMovies` list is populated from the eligible-movies API (movies available as the NEXT pick). The currently-watched movie may or may not appear in this list depending on game state. If the find returns undefined, the component returns null and shows nothing. Cannot verify the data availability without a live session.

**If stats are missing:** The fix would be to fetch the current movie's metadata separately (e.g., a dedicated `/movies/{tmdb_id}` call on session load) rather than relying on the eligible movies list.

---

## Gaps Summary

No gaps found in the automated verification. All 9 items have real implementations, all key links are wired, and no stub anti-patterns were detected.

The one uncertain item (Truth 9 — Now Playing tile stats) has a correct implementation but its data availability depends on runtime state that cannot be verified statically. Human testing is required to confirm the feature surfaces correctly in practice.

---

_Verified: 2026-03-22_
_Verifier: Claude (gsd-verifier)_
