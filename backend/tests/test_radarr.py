"""
GAME-08: RadarrClient — async httpx wrapper for Radarr API v3.

Tests cover:
- movie_exists: Python-side filtering handles Radarr bug #6086
- lookup_movie: returns first result or None
- add_movie: 400 treated as success (not raises)
- get_root_folder: returns first folder path or '/movies'
- get_quality_profile_id: returns first profile id or 1
- close: delegates to httpx AsyncClient.aclose()
"""

import pytest
import httpx
from unittest.mock import AsyncMock, patch, MagicMock

from app.services.radarr import RadarrClient


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_DUMMY_REQUEST = httpx.Request("GET", "http://radarr:7878/api/v3/test")


def _make_response(status_code: int, json_body) -> httpx.Response:
    """Build a fake httpx.Response with .json() returning json_body.

    Attaches a dummy request so raise_for_status() works correctly.
    """
    import json as _json
    return httpx.Response(
        status_code=status_code,
        content=_json.dumps(json_body).encode(),
        headers={"content-type": "application/json"},
        request=_DUMMY_REQUEST,
    )


def _make_client(responses: dict) -> RadarrClient:
    """Return a RadarrClient whose internal _client.get/.post are patched."""
    client = RadarrClient(base_url="http://radarr:7878", api_key="testkey")
    return client


# ---------------------------------------------------------------------------
# movie_exists
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_movie_exists_returns_true_when_found():
    """movie_exists returns True when Radarr returns a list containing the tmdb_id."""
    client = RadarrClient(base_url="http://radarr:7878", api_key="testkey")
    client._client = AsyncMock()
    client._client.get = AsyncMock(return_value=_make_response(200, [{"tmdbId": 123, "title": "Test"}]))

    result = await client.movie_exists(123)
    assert result is True


@pytest.mark.asyncio
async def test_movie_exists_returns_false_when_not_found():
    """movie_exists returns False when Radarr list does not contain the tmdb_id."""
    client = RadarrClient(base_url="http://radarr:7878", api_key="testkey")
    client._client = AsyncMock()
    client._client.get = AsyncMock(return_value=_make_response(200, []))

    result = await client.movie_exists(123)
    assert result is False


@pytest.mark.asyncio
async def test_movie_exists_filters_by_tmdb_id():
    """movie_exists must filter Python-side: a list with a different tmdbId returns False.

    This exercises Radarr bug #6086: GET /api/v3/movie?tmdbId=X may return ALL movies
    on older Radarr installs rather than filtering server-side.
    """
    client = RadarrClient(base_url="http://radarr:7878", api_key="testkey")
    client._client = AsyncMock()
    # Radarr returns a movie with tmdbId=999, but we asked for 123
    client._client.get = AsyncMock(
        return_value=_make_response(200, [{"tmdbId": 999, "title": "Wrong Movie"}])
    )

    result = await client.movie_exists(123)
    assert result is False, "movie_exists must filter by tmdbId in Python, not trust list length"


# ---------------------------------------------------------------------------
# lookup_movie
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_lookup_movie_returns_first_result():
    """lookup_movie returns the first element when Radarr returns results."""
    client = RadarrClient(base_url="http://radarr:7878", api_key="testkey")
    client._client = AsyncMock()
    movie_data = {"tmdbId": 550, "title": "Fight Club", "titleSlug": "fight-club-550"}
    client._client.get = AsyncMock(return_value=_make_response(200, [movie_data, {"tmdbId": 551}]))

    result = await client.lookup_movie(550)
    assert result == movie_data


@pytest.mark.asyncio
async def test_lookup_movie_returns_none_when_empty():
    """lookup_movie returns None when Radarr returns an empty list."""
    client = RadarrClient(base_url="http://radarr:7878", api_key="testkey")
    client._client = AsyncMock()
    client._client.get = AsyncMock(return_value=_make_response(200, []))

    result = await client.lookup_movie(550)
    assert result is None


# ---------------------------------------------------------------------------
# add_movie
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_add_movie_returns_json_on_success():
    """add_movie returns parsed JSON body on 201/200 success."""
    client = RadarrClient(base_url="http://radarr:7878", api_key="testkey")
    client._client = AsyncMock()
    added = {"id": 42, "tmdbId": 550, "title": "Fight Club"}
    client._client.post = AsyncMock(return_value=_make_response(201, added))

    result = await client.add_movie({"tmdbId": 550, "title": "Fight Club"})
    assert result == added


@pytest.mark.asyncio
async def test_add_movie_already_exists_400():
    """add_movie returns {"status": "already_exists"} on HTTP 400 — does NOT raise.

    Radarr returns 400 when a movie already exists in the library.
    This must be treated as a success, not an error.
    """
    client = RadarrClient(base_url="http://radarr:7878", api_key="testkey")
    client._client = AsyncMock()
    client._client.post = AsyncMock(
        return_value=_make_response(400, [{"errorMessage": "This movie has already been added"}])
    )

    result = await client.add_movie({"tmdbId": 550})
    assert result == {"status": "already_exists"}, "HTTP 400 must not raise — return already_exists sentinel"


# ---------------------------------------------------------------------------
# get_root_folder
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_root_folder_returns_first_path():
    """get_root_folder returns the first configured folder path."""
    client = RadarrClient(base_url="http://radarr:7878", api_key="testkey")
    client._client = AsyncMock()
    client._client.get = AsyncMock(
        return_value=_make_response(200, [{"path": "/data/movies"}, {"path": "/data/other"}])
    )

    result = await client.get_root_folder()
    assert result == "/data/movies"


@pytest.mark.asyncio
async def test_get_root_folder_returns_default_when_empty():
    """get_root_folder returns '/movies' fallback when Radarr has no root folders configured."""
    client = RadarrClient(base_url="http://radarr:7878", api_key="testkey")
    client._client = AsyncMock()
    client._client.get = AsyncMock(return_value=_make_response(200, []))

    result = await client.get_root_folder()
    assert result == "/movies"


# ---------------------------------------------------------------------------
# get_quality_profile_id
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_quality_profile_id_returns_first_id():
    """get_quality_profile_id returns the first profile's id."""
    client = RadarrClient(base_url="http://radarr:7878", api_key="testkey")
    client._client = AsyncMock()
    client._client.get = AsyncMock(
        return_value=_make_response(200, [{"id": 5, "name": "HD-1080p"}, {"id": 6, "name": "Any"}])
    )

    result = await client.get_quality_profile_id()
    assert result == 5
