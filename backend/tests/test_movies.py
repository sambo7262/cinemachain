"""
DATA-06: PATCH /movies/{id}/watched stores a watch_events row with source='manual'.
This is the fallback for users without Plex Pass.

Wave 2 (Plan 02-05) adds the PATCH endpoint to app/routers/movies.py.
This test becomes green after Plan 02-05 executes.
"""
import pytest


@pytest.mark.asyncio
async def test_manual_mark_watched(client):
    """DATA-06: PATCH /movies/550/watched returns 200 and marks movie as watched."""
    response = await client.patch("/movies/550/watched")
    assert response.status_code == 200
    body = response.json()
    assert body.get("watched") is True
    assert body.get("source") == "manual"


@pytest.mark.asyncio
async def test_manual_mark_watched_is_idempotent(client):
    """DATA-06: Marking same movie watched twice must not raise an error (ON CONFLICT DO NOTHING)."""
    r1 = await client.patch("/movies/550/watched")
    assert r1.status_code == 200

    r2 = await client.patch("/movies/550/watched")
    assert r2.status_code == 200

    # Both calls succeed; second call is a no-op at DB level
    assert r2.json().get("watched") is True
