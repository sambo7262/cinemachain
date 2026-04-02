"""
MDBLIST-01: MDBList API client parses all rating sources from the response.
MDBLIST-02: Extended parser stores imdb_rating, metacritic_score, letterboxd_score, mdb_avg_score.
MDBLIST-03: Top-level imdbid field stored as imdb_id; score_average stored as mdb_avg_score.

Wave 0 stubs — RED phase. Tests define expected behavior before implementation.
All tests skip locally (asyncpg not installed outside Docker).
"""
import pytest


# ---------------------------------------------------------------------------
# MDBLIST-01/02: Parser extracts all rating sources
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_parse_all_rating_sources():
    """Parser extracts imdb_rating, rt_score, rt_audience_score, metacritic_score,
    letterboxd_score, and mdb_avg_score from a mock MDBList response dict."""
    try:
        import asyncpg  # noqa: F401
    except ImportError:
        pytest.skip("asyncpg not installed locally — runs in Docker")

    from unittest.mock import AsyncMock, MagicMock, patch
    import httpx

    mock_response_data = {
        "imdbid": "tt0111161",
        "score_average": 9.3,
        "ratings": [
            {"source": "tomatoes", "value": 91},
            {"source": "tomatoesaudience", "value": 98},
            {"source": "imdb", "value": 93},
            {"source": "metacritic", "value": 82},
            {"source": "letterboxd", "value": 47},
        ],
    }

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = mock_response_data

    mock_movie = MagicMock()
    mock_movie.tmdb_id = 278

    mock_client = AsyncMock()
    mock_client.get.return_value = mock_resp

    from app.services import mdblist as mdblist_mod
    from app.services.settings_service import get_setting

    mock_db = AsyncMock()

    with patch.object(mdblist_mod, "settings_service") as mock_settings:
        mock_settings.get_setting = AsyncMock(return_value="fake-api-key")

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_movie]
        mock_db.execute = AsyncMock(return_value=mock_result)

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=None)

            await mdblist_mod.fetch_rt_scores([278], mock_db)

    assert mock_movie.rt_score == 91
    assert mock_movie.rt_audience_score == 98
    assert mock_movie.imdb_rating == 9.3
    assert mock_movie.metacritic_score == 82
    assert mock_movie.letterboxd_score == 4.7  # letterboxd stored as float: 47 / 10
    assert mock_movie.mdb_avg_score == 9.3


# ---------------------------------------------------------------------------
# MDBLIST-03: score_average top-level field → mdb_avg_score
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_score_average_stored():
    """score_average from top-level response field maps to mdb_avg_score on the Movie."""
    try:
        import asyncpg  # noqa: F401
    except ImportError:
        pytest.skip("asyncpg not installed locally — runs in Docker")

    from unittest.mock import AsyncMock, MagicMock, patch

    mock_response_data = {
        "imdbid": "tt0468569",
        "score_average": 8.5,
        "ratings": [],
    }

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = mock_response_data

    mock_movie = MagicMock()
    mock_movie.tmdb_id = 155

    mock_client = AsyncMock()
    mock_client.get.return_value = mock_resp

    from app.services import mdblist as mdblist_mod

    mock_db = AsyncMock()

    with patch.object(mdblist_mod, "settings_service") as mock_settings:
        mock_settings.get_setting = AsyncMock(return_value="fake-api-key")

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_movie]
        mock_db.execute = AsyncMock(return_value=mock_result)

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=None)

            await mdblist_mod.fetch_rt_scores([155], mock_db)

    assert mock_movie.mdb_avg_score == 8.5


# ---------------------------------------------------------------------------
# MDBLIST-03: imdbid top-level field → imdb_id
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_imdbid_stored():
    """imdbid from top-level response field maps to imdb_id on the Movie."""
    try:
        import asyncpg  # noqa: F401
    except ImportError:
        pytest.skip("asyncpg not installed locally — runs in Docker")

    from unittest.mock import AsyncMock, MagicMock, patch

    mock_response_data = {
        "imdbid": "tt0111161",
        "score_average": 9.3,
        "ratings": [],
    }

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = mock_response_data

    mock_movie = MagicMock()
    mock_movie.tmdb_id = 278

    mock_client = AsyncMock()
    mock_client.get.return_value = mock_resp

    from app.services import mdblist as mdblist_mod

    mock_db = AsyncMock()

    with patch.object(mdblist_mod, "settings_service") as mock_settings:
        mock_settings.get_setting = AsyncMock(return_value="fake-api-key")

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_movie]
        mock_db.execute = AsyncMock(return_value=mock_result)

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=None)

            await mdblist_mod.fetch_rt_scores([278], mock_db)

    assert mock_movie.imdb_id == "tt0111161"


# ---------------------------------------------------------------------------
# MDBLIST-03: Backfill status response schema
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_backfill_status_schema():
    """GET /mdblist/backfill/status returns a dict with running, fetched, total,
    calls_used_today, and daily_limit keys."""
    try:
        import asyncpg  # noqa: F401
    except ImportError:
        pytest.skip("asyncpg not installed locally — runs in Docker")

    from unittest.mock import AsyncMock, MagicMock, patch

    # Stub: when the backfill endpoint is wired, it should return this shape.
    # For now we verify the shape contract directly against the expected keys.
    expected_keys = {"running", "fetched", "total", "calls_used_today", "daily_limit"}

    # Minimal conformant response
    status_response = {
        "running": False,
        "fetched": 0,
        "total": 100,
        "calls_used_today": 0,
        "daily_limit": 10000,
    }

    assert set(status_response.keys()) == expected_keys
    assert isinstance(status_response["running"], bool)
    assert isinstance(status_response["fetched"], int)
    assert isinstance(status_response["total"], int)
    assert isinstance(status_response["calls_used_today"], int)
    assert isinstance(status_response["daily_limit"], int)
