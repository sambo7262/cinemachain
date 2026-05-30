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


# Phase 22 STALE-01 / STALE-03 — force-refresh helper + manual refresh endpoint


# Broader skip pattern (matches Plan 22-01 test_game.py): probe import wrapped in
# try/except Exception so tests skip cleanly in any local environment without a
# wired .env (asyncpg-only catch misses pydantic ValidationError on missing env).
try:
    from app.services.cache import refresh_top_actors_force as _probe_refresh  # noqa: F401
    from app.routers.cache import refresh_actor_filmographies_now as _probe_endpoint  # noqa: F401
    _CACHE_IMPORTABLE = True
except Exception:
    _CACHE_IMPORTABLE = False


@pytest.mark.asyncio
async def test_refresh_top_actors_force_passes_force_refresh_true():
    """Phase 22 STALE-01: refresh_top_actors_force calls _ensure_actor_credits_in_db with force_refresh=True."""
    if not _CACHE_IMPORTABLE:
        pytest.skip("app.services.cache not yet importable (asyncpg or env missing)")
    from app.services.cache import refresh_top_actors_force

    mock_tmdb = AsyncMock()
    with patch("app.services.cache._ensure_actor_credits_in_db", new_callable=AsyncMock) as mock_ensure, \
         patch("app.services.cache._bg_session_factory") as mock_factory:
        mock_session = AsyncMock()
        mock_factory.return_value.__aenter__.return_value = mock_session

        await refresh_top_actors_force(mock_tmdb, [100, 200, 300], vote_threshold=5)

        assert mock_ensure.call_count == 3
        for call in mock_ensure.call_args_list:
            assert call.kwargs.get("force_refresh") is True, \
                "every call must pass force_refresh=True"


@pytest.mark.asyncio
async def test_refresh_now_endpoint_returns_running_when_already_running():
    """Phase 22 STALE-03: POST /cache/actors/refresh-now returns {running: True} when _cache_state.running is already True."""
    if not _CACHE_IMPORTABLE:
        pytest.skip("app.routers.cache not yet importable (asyncpg or env missing)")
    from app.services.cache import _cache_state
    from app.routers.cache import refresh_actor_filmographies_now

    mock_bg = MagicMock()
    mock_request = MagicMock()

    _cache_state.running = True
    try:
        result = await refresh_actor_filmographies_now(mock_bg, mock_request)
        assert result == {"running": True}
        # Background task must NOT be scheduled when guard is hit
        assert mock_bg.add_task.call_count == 0
    finally:
        _cache_state.running = False


# ===== Phase 23 HEALTH-01 — MPAA sentinel + query fix =====

try:
    from app.services.cache import _backfill_mpaa_pass as _probe_mpaa  # noqa: F401
    _MPAA_IMPORTABLE = True
except Exception:
    _MPAA_IMPORTABLE = False


def _make_mpaa_tmdb_mock(release_dates_json):
    """Helper: build a TMDB client mock returning the given release_dates payload."""
    mock_tmdb = MagicMock()
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = release_dates_json
    mock_response.raise_for_status = MagicMock()
    # _sem is an async context manager
    mock_tmdb._sem = AsyncMock()
    mock_tmdb._sem.__aenter__ = AsyncMock(return_value=None)
    mock_tmdb._sem.__aexit__ = AsyncMock(return_value=False)
    mock_tmdb._client.get = AsyncMock(return_value=mock_response)
    return mock_tmdb


def _make_bg_session_mock(returned_ids):
    """Helper: build a _bg_session_factory mock yielding a session whose SELECT
    returns the given tmdb_ids and whose UPDATE captures values."""
    mock_db = AsyncMock()
    mock_db.__aenter__ = AsyncMock(return_value=mock_db)
    mock_db.__aexit__ = AsyncMock(return_value=False)
    mock_result = MagicMock()
    mock_result.all.return_value = [(tid,) for tid in returned_ids]
    mock_db.execute = AsyncMock(return_value=mock_result)
    mock_db.commit = AsyncMock()
    return mock_db


@pytest.mark.asyncio
async def test_backfill_mpaa_writes_nr_when_tmdb_returns_no_us_cert():
    """HEALTH-01: _backfill_mpaa_pass writes 'NR' (not '') when TMDB has no US cert."""
    if not _MPAA_IMPORTABLE:
        pytest.skip("app.services.cache not yet importable (asyncpg or env missing)")
    from app.services.cache import _backfill_mpaa_pass

    mock_tmdb = _make_mpaa_tmdb_mock({"results": []})  # no US country block
    mock_db = _make_bg_session_mock([12345])

    update_values = []

    async def capture_execute(stmt):
        # The UPDATE stmt is sa_update(Movie)...values(mpaa_rating=cert)
        try:
            compiled = stmt.compile(compile_kwargs={"literal_binds": True})
            update_values.append(str(compiled))
        except Exception:
            pass
        return MagicMock(all=MagicMock(return_value=[(12345,)]))

    mock_db.execute = AsyncMock(side_effect=capture_execute)

    with patch("app.services.cache._bg_session_factory", return_value=mock_db):
        await _backfill_mpaa_pass(mock_tmdb, limit=10)

    # Find the UPDATE statement among captured executions
    update_stmts = [s for s in update_values if "UPDATE" in s.upper() and "mpaa_rating" in s]
    assert any("'NR'" in s for s in update_stmts), (
        f"Expected an UPDATE writing 'NR' sentinel; got: {update_stmts}"
    )
    assert not any("mpaa_rating = ''" in s for s in update_stmts), (
        f"Must NOT write empty-string sentinel anymore; got: {update_stmts}"
    )


@pytest.mark.asyncio
async def test_backfill_mpaa_writes_actual_cert_when_present():
    """HEALTH-01: real US certification wins over 'NR' sentinel."""
    if not _MPAA_IMPORTABLE:
        pytest.skip("app.services.cache not yet importable (asyncpg or env missing)")
    from app.services.cache import _backfill_mpaa_pass

    mock_tmdb = _make_mpaa_tmdb_mock({
        "results": [
            {"iso_3166_1": "US", "release_dates": [{"certification": "R"}]}
        ]
    })
    mock_db = _make_bg_session_mock([12345])

    captured = []
    async def capture_execute(stmt):
        try:
            compiled = stmt.compile(compile_kwargs={"literal_binds": True})
            captured.append(str(compiled))
        except Exception:
            pass
        return MagicMock(all=MagicMock(return_value=[(12345,)]))
    mock_db.execute = AsyncMock(side_effect=capture_execute)

    with patch("app.services.cache._bg_session_factory", return_value=mock_db):
        await _backfill_mpaa_pass(mock_tmdb, limit=10)

    update_stmts = [s for s in captured if "UPDATE" in s.upper() and "mpaa_rating" in s]
    assert any("'R'" in s for s in update_stmts), (
        f"Expected an UPDATE writing 'R' real certification; got: {update_stmts}"
    )


@pytest.mark.asyncio
async def test_backfill_mpaa_query_targets_null_only():
    """HEALTH-01: SELECT filters mpaa_rating IS NULL only (no '' OR clause)."""
    if not _MPAA_IMPORTABLE:
        pytest.skip("app.services.cache not yet importable (asyncpg or env missing)")
    from app.services.cache import _backfill_mpaa_pass

    mock_tmdb = _make_mpaa_tmdb_mock({"results": []})
    mock_db = _make_bg_session_mock([])  # no rows — work loop won't run

    captured_selects = []
    async def capture_execute(stmt):
        try:
            compiled = stmt.compile(compile_kwargs={"literal_binds": True})
            sql = str(compiled)
            if "SELECT" in sql.upper():
                captured_selects.append(sql)
        except Exception:
            pass
        return MagicMock(all=MagicMock(return_value=[]))
    mock_db.execute = AsyncMock(side_effect=capture_execute)

    with patch("app.services.cache._bg_session_factory", return_value=mock_db):
        await _backfill_mpaa_pass(mock_tmdb, limit=10)

    assert captured_selects, "Expected at least one SELECT against movies.mpaa_rating"
    first = captured_selects[0]
    assert "IS NULL" in first.upper(), f"Expected IS NULL filter; got: {first}"
    assert "mpaa_rating = ''" not in first, (
        f"Empty-string OR clause must be removed; got: {first}"
    )


@pytest.mark.asyncio
async def test_backfill_mpaa_skips_when_no_null_rows():
    """HEALTH-01: zero NULL rows → zero TMDB calls (NR-stamped rows are excluded)."""
    if not _MPAA_IMPORTABLE:
        pytest.skip("app.services.cache not yet importable (asyncpg or env missing)")
    from app.services.cache import _backfill_mpaa_pass

    mock_tmdb = _make_mpaa_tmdb_mock({"results": []})
    mock_db = _make_bg_session_mock([])  # DB returns no rows to process

    with patch("app.services.cache._bg_session_factory", return_value=mock_db):
        await _backfill_mpaa_pass(mock_tmdb, limit=10)

    assert mock_tmdb._client.get.call_count == 0, (
        "No TMDB calls should fire when the work set is empty"
    )
