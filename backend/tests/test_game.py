"""
GAME-01: POST /game/sessions creates a new active game session.
GAME-02: POST /game/sessions with movie title (not just watched) creates a session.
GAME-03: POST /game/sessions when active session exists returns 409.
GAME-04: GET /game/sessions/active returns the current active session.
GAME-05: GET /game/sessions/{id}/eligible-actors returns actors from current movie, excluding already-picked ones.
GAME-06: GET /game/sessions/{id}/eligible-movies returns unwatched filmography for a given actor.
GAME-07: POST /game/sessions/{id}/pick-actor records the actor choice and advances the session.
GAME-08: POST /game/sessions/{id}/request-movie calls Radarr to queue the selected movie.

Additional behaviors:
  - eligible-movies with sort=rating returns descending vote_average order
  - eligible-movies with all_movies=true includes watched movies with selectable=False
  - pause/resume/end session status transitions
  - POST /game/sessions/import-csv creates session with pre-populated steps

Wave 1 (Plan 03-02) implements the routes and game engine.
These stubs define the RED phase — they must collect and fail, not pass.
"""
import pytest
from unittest.mock import AsyncMock


# ---------------------------------------------------------------------------
# GAME-01: Create session
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_session(client):
    """GAME-01: POST /game/sessions creates session from a watched movie, returns 201 with id and status='active'."""
    pytest.fail("not implemented")


@pytest.mark.asyncio
async def test_create_session_with_title_search(client):
    """GAME-02: POST /game/sessions with a movie title (not just a watched movie) creates a valid session."""
    pytest.fail("not implemented")


# ---------------------------------------------------------------------------
# GAME-03: Conflict when session already active
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_session_conflict(client):
    """GAME-03: POST /game/sessions when an active session already exists returns 409."""
    pytest.fail("not implemented")


# ---------------------------------------------------------------------------
# GAME-04: Get active session
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_active_session(client):
    """GAME-04: GET /game/sessions/active returns the current active session."""
    pytest.fail("not implemented")


# ---------------------------------------------------------------------------
# GAME-05: Eligible actors (excludes already picked)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_eligible_actors_excludes_picked(client):
    """GAME-05: GET /game/sessions/{id}/eligible-actors excludes actors already recorded in session steps."""
    pytest.fail("not implemented")


@pytest.mark.asyncio
async def test_eligible_actors_empty_when_all_picked(client):
    """GAME-05: GET /game/sessions/{id}/eligible-actors returns empty list when all cast members have been picked."""
    pytest.fail("not implemented")


# ---------------------------------------------------------------------------
# GAME-06: Eligible movies
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_eligible_movies(client):
    """GAME-06: GET /game/sessions/{id}/eligible-movies returns the actor's unwatched filmography."""
    pytest.fail("not implemented")


@pytest.mark.asyncio
async def test_eligible_movies_combined_view(client):
    """GAME-06: GET /game/sessions/{id}/eligible-movies without an actor param returns eligible movies across all current eligible actors."""
    pytest.fail("not implemented")


# ---------------------------------------------------------------------------
# GAME-07: Pick actor
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_pick_actor_persisted(client):
    """GAME-07: POST /game/sessions/{id}/pick-actor records a GameSessionStep and returns the updated session."""
    pytest.fail("not implemented")


@pytest.mark.asyncio
async def test_pick_actor_already_picked(client):
    """GAME-07: POST /game/sessions/{id}/pick-actor with an already-picked actor returns 409."""
    pytest.fail("not implemented")


# ---------------------------------------------------------------------------
# GAME-06 (sort / filter variations)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_sort_movies(client):
    """GAME-06: eligible-movies with sort=rating returns movies in descending vote_average order."""
    pytest.fail("not implemented")


@pytest.mark.asyncio
async def test_all_movies_toggle(client):
    """GAME-06: eligible-movies with all_movies=true returns watched movies with watched=True flag; watched movies have selectable=False."""
    pytest.fail("not implemented")


@pytest.mark.asyncio
async def test_watched_not_selectable(client):
    """GAME-06: A watched movie appearing in eligible-movies has selectable=False."""
    pytest.fail("not implemented")


# ---------------------------------------------------------------------------
# GAME-08: Request movie via Radarr
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_request_movie_radarr(client):
    """GAME-08: POST /game/sessions/{id}/request-movie calls RadarrClient.add_movie when movie is not already in Radarr."""
    pytest.fail("not implemented")


@pytest.mark.asyncio
async def test_request_movie_skip_radarr(client):
    """GAME-08: POST /game/sessions/{id}/request-movie skips Radarr when movie already exists; returns status='already_in_radarr'."""
    pytest.fail("not implemented")


# ---------------------------------------------------------------------------
# Session lifecycle: pause / resume / end
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_pause_session(client):
    """POST /game/sessions/{id}/pause sets status='paused', returns 200."""
    pytest.fail("not implemented")


@pytest.mark.asyncio
async def test_resume_session(client):
    """POST /game/sessions/{id}/resume sets status='active', returns 200."""
    pytest.fail("not implemented")


@pytest.mark.asyncio
async def test_end_session(client):
    """POST /game/sessions/{id}/end sets status='ended', returns 200."""
    pytest.fail("not implemented")


# ---------------------------------------------------------------------------
# CSV import
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_import_csv(client):
    """POST /game/sessions/import-csv with valid CSV rows creates a session with pre-populated steps."""
    pytest.fail("not implemented")
