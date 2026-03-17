"""Tests for nightly TMDB cache job (CACHE-01, CACHE-02)."""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_nightly_cache_job_fetches_top_n_movies(client: AsyncClient):
    """CACHE-01: nightly_cache_job() pages through TMDB discover endpoint and inserts movies into DB."""
    pytest.skip("not implemented — requires nightly_cache_job in services/cache.py")


@pytest.mark.asyncio
async def test_nightly_cache_job_skips_already_cached(client: AsyncClient):
    """CACHE-01: nightly_cache_job() skips movies where fetched_at IS NOT NULL AND genres IS NOT NULL."""
    pytest.skip("not implemented — requires nightly_cache_job in services/cache.py")


@pytest.mark.asyncio
async def test_lazy_enrich_populates_genres_and_runtime(client: AsyncClient):
    """CACHE-02: Movies with genres IS NULL get genres and runtime populated by _ensure_movie_details_in_db."""
    pytest.skip("not implemented — requires _ensure_movie_details_in_db importable from services/cache.py")
