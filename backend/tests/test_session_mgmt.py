"""Tests for session management endpoints (SESSION-01, SESSION-02)."""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_delete_last_step_removes_step_and_reverts_movie(client: AsyncClient):
    """SESSION-01: DELETE /game/sessions/{id}/steps/last removes highest step_order step
    and reverts current_movie_tmdb_id to the previous step's movie_tmdb_id."""
    pytest.skip("not implemented — requires DELETE /game/sessions/{id}/steps/last endpoint")


@pytest.mark.asyncio
async def test_delete_last_step_blocked_on_single_step_session(client: AsyncClient):
    """SESSION-01: DELETE /game/sessions/{id}/steps/last returns 400 when only 1 step remains."""
    pytest.skip("not implemented — single-step guard not implemented")


@pytest.mark.asyncio
async def test_delete_archived_session_removes_session_and_steps(client: AsyncClient):
    """SESSION-02: DELETE /game/sessions/{id} permanently removes an archived session and all its steps."""
    pytest.skip("not implemented — requires DELETE /game/sessions/{id} endpoint")


@pytest.mark.asyncio
async def test_delete_archived_session_blocked_on_active_session(client: AsyncClient):
    """SESSION-02: DELETE /game/sessions/{id} returns 403 when session status is not 'archived'."""
    pytest.skip("not implemented — status guard not implemented")
