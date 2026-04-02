"""
SUGGEST-01: TMDB recommendations are fetched and cached per movie row.
SUGGEST-01: get_session_suggestions returns IDs ranked by frequency across last N watched movies.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock


def _make_db_execute(scalar_one_or_none_return=None, all_return=None):
    """Helper: build a mock db.execute that returns a result supporting both
    .scalar_one_or_none() and .all() depending on what the caller needs."""
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = scalar_one_or_none_return
    mock_result.all.return_value = all_return or []
    return AsyncMock(return_value=mock_result)


# ---------------------------------------------------------------------------
# fetch_and_cache_recommendations
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_fetch_and_cache_hit():
    """Cache hit: when movie.tmdb_recommendations is already set, tmdb.fetch_recommendations
    is NOT called."""
    try:
        import asyncpg  # noqa: F401
    except ImportError:
        pytest.skip("asyncpg not installed locally — runs in Docker")

    from app.services.suggestions import fetch_and_cache_recommendations

    mock_movie = MagicMock()
    mock_movie.tmdb_recommendations = [111, 222, 333]

    mock_db = AsyncMock()
    mock_db.execute = _make_db_execute(scalar_one_or_none_return=mock_movie)

    mock_tmdb = AsyncMock()
    mock_tmdb.fetch_recommendations = AsyncMock()

    result = await fetch_and_cache_recommendations(550, mock_db, mock_tmdb)

    mock_tmdb.fetch_recommendations.assert_not_called()
    assert result == [111, 222, 333]


@pytest.mark.asyncio
async def test_fetch_and_cache_miss():
    """Cache miss: when movie.tmdb_recommendations is None, TMDB is called and result stored."""
    try:
        import asyncpg  # noqa: F401
    except ImportError:
        pytest.skip("asyncpg not installed locally — runs in Docker")

    from app.services.suggestions import fetch_and_cache_recommendations

    mock_movie = MagicMock()
    mock_movie.tmdb_recommendations = None

    mock_db = AsyncMock()
    mock_db.execute = _make_db_execute(scalar_one_or_none_return=mock_movie)
    mock_db.commit = AsyncMock()

    mock_tmdb = AsyncMock()
    mock_tmdb.fetch_recommendations = AsyncMock(
        return_value={"results": [{"id": 10}, {"id": 20}]}
    )

    result = await fetch_and_cache_recommendations(550, mock_db, mock_tmdb)

    mock_tmdb.fetch_recommendations.assert_called_once_with(550)
    assert result == [10, 20]
    assert mock_movie.tmdb_recommendations == [10, 20]
    mock_db.commit.assert_called_once()


@pytest.mark.asyncio
async def test_fetch_writes_empty_list_on_no_results():
    """Empty TMDB results write [] (not None) so future calls hit the cache, not TMDB."""
    try:
        import asyncpg  # noqa: F401
    except ImportError:
        pytest.skip("asyncpg not installed locally — runs in Docker")

    from app.services.suggestions import fetch_and_cache_recommendations

    mock_movie = MagicMock()
    mock_movie.tmdb_recommendations = None

    mock_db = AsyncMock()
    mock_db.execute = _make_db_execute(scalar_one_or_none_return=mock_movie)
    mock_db.commit = AsyncMock()

    mock_tmdb = AsyncMock()
    mock_tmdb.fetch_recommendations = AsyncMock(return_value={"results": []})

    result = await fetch_and_cache_recommendations(550, mock_db, mock_tmdb)

    assert result == []
    assert mock_movie.tmdb_recommendations == []  # written, not left as None
    mock_db.commit.assert_called_once()


@pytest.mark.asyncio
async def test_fetch_returns_empty_when_movie_not_in_db():
    """Returns [] when no movie row is found for the given tmdb_id."""
    try:
        import asyncpg  # noqa: F401
    except ImportError:
        pytest.skip("asyncpg not installed locally — runs in Docker")

    from app.services.suggestions import fetch_and_cache_recommendations

    mock_db = AsyncMock()
    mock_db.execute = _make_db_execute(scalar_one_or_none_return=None)

    mock_tmdb = AsyncMock()
    mock_tmdb.fetch_recommendations = AsyncMock()

    result = await fetch_and_cache_recommendations(999, mock_db, mock_tmdb)

    assert result == []
    mock_tmdb.fetch_recommendations.assert_not_called()


# ---------------------------------------------------------------------------
# get_session_suggestions
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_session_suggestions_empty_when_no_watches():
    """Returns [] when there are no WatchEvents."""
    try:
        import asyncpg  # noqa: F401
    except ImportError:
        pytest.skip("asyncpg not installed locally — runs in Docker")

    from app.services.suggestions import get_session_suggestions

    mock_db = AsyncMock()
    # WatchEvent query returns no rows
    mock_watch_result = MagicMock()
    mock_watch_result.all.return_value = []
    mock_db.execute = AsyncMock(return_value=mock_watch_result)

    mock_tmdb = AsyncMock()

    result = await get_session_suggestions(mock_db, mock_tmdb, n=5)

    assert result == []


@pytest.mark.asyncio
async def test_get_session_suggestions_frequency_ranking():
    """Movie recommended by 2 seed movies ranks above one recommended by only 1 seed.
    Seed movies themselves are excluded from results."""
    try:
        import asyncpg  # noqa: F401
    except ImportError:
        pytest.skip("asyncpg not installed locally — runs in Docker")

    from app.services.suggestions import get_session_suggestions

    # Three seed movies (>= 3 seeds → min_freq=2)
    # Movie 999 appears in seeds 100 and 200 (freq=2) — must appear
    # Movie 888 appears only in seed 100 (freq=1) — excluded
    # Movie 777 appears only in seed 200 (freq=1) — excluded
    # Movie 100, 200, 300 are seeds — excluded

    seed_rows = [(100,), (200,), (300,)]

    movie_100 = MagicMock()
    movie_100.tmdb_recommendations = [999, 888]

    movie_200 = MagicMock()
    movie_200.tmdb_recommendations = [999, 777]

    movie_300 = MagicMock()
    movie_300.tmdb_recommendations = [555]

    call_count = 0

    async def fake_execute(stmt):
        nonlocal call_count
        call_count += 1
        mock_result = MagicMock()
        if call_count == 1:
            mock_result.all.return_value = seed_rows
            mock_result.scalar_one_or_none.return_value = None
        elif call_count == 2:
            mock_result.scalar_one_or_none.return_value = movie_100
        elif call_count == 3:
            mock_result.scalar_one_or_none.return_value = movie_200
        elif call_count == 4:
            mock_result.scalar_one_or_none.return_value = movie_300
        return mock_result

    mock_db = AsyncMock()
    mock_db.execute = fake_execute

    mock_tmdb = AsyncMock()

    result = await get_session_suggestions(mock_db, mock_tmdb, n=5)

    # 999 has freq=2 — must appear and rank first
    assert 999 in result
    assert result[0] == 999
    # Single-seed recs excluded (min_freq=2 with 3 seeds)
    assert 888 not in result
    assert 777 not in result
    assert 555 not in result
    # Seeds excluded
    assert 100 not in result
    assert 200 not in result
    assert 300 not in result
