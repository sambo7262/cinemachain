"""Integration tests for session management endpoints (SESSION-01, SESSION-02)."""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_delete_last_step_removes_step_and_reverts_movie(client: AsyncClient):
    """SESSION-01: DELETE removes highest step, reverts current_movie_tmdb_id to prior step."""
    # Create a session with a known starting movie
    create_resp = await client.post("/game/sessions", json={
        "start_movie_tmdb_id": 550,
        "name": "test-delete-step",
        "start_movie_title": "Fight Club",
    })
    assert create_resp.status_code == 201
    session_id = create_resp.json()["id"]

    # Pick an actor to advance the session (creates step 2)
    pick_resp = await client.post(f"/game/sessions/{session_id}/pick-actor", json={
        "actor_tmdb_id": 819,
        "actor_name": "Edward Norton",
    })
    assert pick_resp.status_code == 200
    assert len(pick_resp.json()["steps"]) == 2

    # Delete last step
    del_resp = await client.delete(f"/game/sessions/{session_id}/steps/last")
    assert del_resp.status_code == 200
    data = del_resp.json()
    assert len(data["steps"]) == 1
    assert data["current_movie_tmdb_id"] == 550  # reverted to starting movie


@pytest.mark.asyncio
async def test_delete_last_step_blocked_on_single_step_session(client: AsyncClient):
    """SESSION-01: Returns 400 when only 1 step remains."""
    create_resp = await client.post("/game/sessions", json={
        "start_movie_tmdb_id": 550,
        "name": "test-single-step",
        "start_movie_title": "Fight Club",
    })
    assert create_resp.status_code == 201
    session_id = create_resp.json()["id"]

    del_resp = await client.delete(f"/game/sessions/{session_id}/steps/last")
    assert del_resp.status_code == 400
    assert "starting movie" in del_resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_delete_archived_session_removes_session_and_steps(client: AsyncClient):
    """SESSION-02: DELETE permanently removes archived session; subsequent GET returns 404."""
    create_resp = await client.post("/game/sessions", json={
        "start_movie_tmdb_id": 550,
        "name": "test-archive-delete",
        "start_movie_title": "Fight Club",
    })
    assert create_resp.status_code == 201
    session_id = create_resp.json()["id"]

    archive_resp = await client.post(f"/game/sessions/{session_id}/archive")
    assert archive_resp.status_code == 200

    del_resp = await client.delete(f"/game/sessions/{session_id}")
    assert del_resp.status_code == 204

    get_resp = await client.get(f"/game/sessions/{session_id}")
    assert get_resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_archived_session_blocked_on_active_session(client: AsyncClient):
    """SESSION-02: Returns 403 when session is not archived."""
    create_resp = await client.post("/game/sessions", json={
        "start_movie_tmdb_id": 550,
        "name": "test-active-guard",
        "start_movie_title": "Fight Club",
    })
    assert create_resp.status_code == 201
    session_id = create_resp.json()["id"]

    del_resp = await client.delete(f"/game/sessions/{session_id}")
    assert del_resp.status_code == 403
    assert "archived" in del_resp.json()["detail"].lower()
