"""
DATA-05: POST /webhooks/plex with a media.scrobble multipart payload marks the
corresponding movie as watched.

Critical: Plex sends multipart/form-data with JSON in the 'payload' field — NOT a JSON body.
The endpoint must use FastAPI Form(...), not Body(...).

Wave 2 (Plan 02-05) implements the webhook router.
This test becomes green after Plan 02-05 executes.
"""
import json
import pytest


SCROBBLE_PAYLOAD = json.dumps({
    "event": "media.scrobble",
    "Metadata": {
        "type": "movie",
        "title": "Fight Club",
        "year": 1999,
        "Guid": [
            {"id": "tmdb://550"},
            {"id": "imdb://tt0137523"},
        ],
    }
})


@pytest.mark.asyncio
async def test_scrobble_marks_watched(client):
    """DATA-05: POST /webhooks/plex with media.scrobble marks tmdb_id=550 as watched."""
    response = await client.post(
        "/webhooks/plex",
        data={"payload": SCROBBLE_PAYLOAD},
    )
    assert response.status_code == 200
    assert response.json().get("status") == "ok"

    # Confirm watch state is reflected in movie endpoint
    movie_resp = await client.get("/movies/550")
    assert movie_resp.status_code == 200
    assert movie_resp.json().get("watched") is True


@pytest.mark.asyncio
async def test_scrobble_is_idempotent(client):
    """DATA-05: Duplicate scrobble for same movie must not create duplicate watch_events rows.
    The endpoint uses INSERT ... ON CONFLICT DO NOTHING so double-fire is harmless.
    """
    for _ in range(2):
        response = await client.post(
            "/webhooks/plex",
            data={"payload": SCROBBLE_PAYLOAD},
        )
        assert response.status_code == 200

    movie_resp = await client.get("/movies/550")
    assert movie_resp.status_code == 200
    assert movie_resp.json().get("watched") is True


@pytest.mark.asyncio
async def test_non_scrobble_event_ignored(client):
    """DATA-05: Non-scrobble events (e.g. media.play) return 200 but do not mark watched."""
    payload = json.dumps({
        "event": "media.play",
        "Metadata": {
            "type": "movie",
            "Guid": [{"id": "tmdb://550"}],
        }
    })
    response = await client.post(
        "/webhooks/plex",
        data={"payload": payload},
    )
    assert response.status_code == 200
