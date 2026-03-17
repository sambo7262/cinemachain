"""Tests for nightly TMDB cache job (CACHE-01, CACHE-02)."""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock


@pytest.mark.asyncio
async def test_nightly_cache_job_calls_ensure_helpers():
    """CACHE-01: nightly_cache_job calls _ensure_movie_cast_in_db for uncached movies."""
    try:
        from app.services.cache import nightly_cache_job
    except ImportError:
        pytest.skip("app.services.cache not yet implemented")

    mock_tmdb = MagicMock()
    mock_response = MagicMock()
    mock_response.json.return_value = {"results": [{"id": 550}, {"id": 551}]}
    mock_response.raise_for_status = MagicMock()

    # Second page returns empty to stop pagination
    mock_tmdb._client.get = AsyncMock(side_effect=[mock_response, MagicMock(**{
        "raise_for_status": MagicMock(),
        "json.return_value": {"results": []},
    })])

    with patch("app.services.cache._ensure_movie_cast_in_db", new_callable=AsyncMock) as mock_cast, \
         patch("app.services.cache._ensure_movie_details_in_db", new_callable=AsyncMock), \
         patch("app.services.cache._bg_session_factory") as mock_factory:
        # Simulate no already-cached movies
        mock_db = AsyncMock()
        mock_db.__aenter__ = AsyncMock(return_value=mock_db)
        mock_db.__aexit__ = AsyncMock(return_value=False)
        mock_result = MagicMock()
        mock_result.all.return_value = []
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_factory.return_value = mock_db

        await nightly_cache_job(mock_tmdb, top_n=2)
        assert mock_cast.call_count == 2  # one call per uncached movie


@pytest.mark.asyncio
async def test_nightly_cache_job_skips_already_cached():
    """CACHE-01: nightly_cache_job skips movies already in DB (fetched_at + genres present)."""
    try:
        from app.services.cache import nightly_cache_job
    except ImportError:
        pytest.skip("app.services.cache not yet implemented")

    mock_tmdb = MagicMock()
    mock_response = MagicMock()
    mock_response.json.return_value = {"results": [{"id": 550}]}
    mock_response.raise_for_status = MagicMock()
    mock_tmdb._client.get = AsyncMock(side_effect=[mock_response, MagicMock(**{
        "raise_for_status": MagicMock(),
        "json.return_value": {"results": []},
    })])

    with patch("app.services.cache._ensure_movie_cast_in_db", new_callable=AsyncMock) as mock_cast, \
         patch("app.services.cache._ensure_movie_details_in_db", new_callable=AsyncMock), \
         patch("app.services.cache._bg_session_factory") as mock_factory:
        mock_db = AsyncMock()
        mock_db.__aenter__ = AsyncMock(return_value=mock_db)
        mock_db.__aexit__ = AsyncMock(return_value=False)
        mock_result = MagicMock()
        mock_result.all.return_value = [(550,)]  # 550 already cached
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_factory.return_value = mock_db

        await nightly_cache_job(mock_tmdb, top_n=1)
        assert mock_cast.call_count == 0  # skipped — already cached


@pytest.mark.asyncio
async def test_lazy_enrich_populates_genres_and_runtime():
    """CACHE-02: _ensure_movie_details_in_db is called for movies with genres IS NULL."""
    # This test verifies the nightly job calls the enrichment helper for stub movies.
    # Integration coverage — the helper itself is tested in test_game.py.
    try:
        from app.services.cache import nightly_cache_job
    except ImportError:
        pytest.skip("app.services.cache not yet implemented")

    mock_tmdb = MagicMock()
    mock_response = MagicMock()
    mock_response.json.return_value = {"results": [{"id": 999}]}
    mock_response.raise_for_status = MagicMock()
    mock_tmdb._client.get = AsyncMock(side_effect=[mock_response, MagicMock(**{
        "raise_for_status": MagicMock(),
        "json.return_value": {"results": []},
    })])

    with patch("app.services.cache._ensure_movie_cast_in_db", new_callable=AsyncMock), \
         patch("app.services.cache._ensure_movie_details_in_db", new_callable=AsyncMock) as mock_enrich, \
         patch("app.services.cache._bg_session_factory") as mock_factory:
        mock_db = AsyncMock()
        mock_db.__aenter__ = AsyncMock(return_value=mock_db)
        mock_db.__aexit__ = AsyncMock(return_value=False)
        mock_result = MagicMock()
        mock_result.all.return_value = []  # movie 999 not cached
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_factory.return_value = mock_db

        await nightly_cache_job(mock_tmdb, top_n=1)
        assert mock_enrich.call_count == 1  # enrichment called for stub movie
        call_args = mock_enrich.call_args[0]
        assert 999 in call_args[0]  # tmdb_id in the ids list
