from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

import httpx

from app.db import get_db
from app.services import settings_service
from app.services.tmdb import TMDBClient
from app.services.radarr import RadarrClient
from app.services.mdblist import test_mdblist_connection
from app.utils.masking import mask_key, is_masked_sentinel, register_secret

router = APIRouter(prefix="/settings", tags=["settings"])

_SECRET_FIELDS = {"tmdb_api_key", "radarr_api_key", "mdblist_api_key"}


def _mask_settings_response(data: dict) -> dict:
    """Apply mask_key() to all secret fields. Non-secret fields returned as-is."""
    result = dict(data)
    for field in _SECRET_FIELDS:
        if field in result:
            result[field] = mask_key(result[field])
    return result


class SettingsResponse(BaseModel):
    tmdb_api_key: str | None = None
    radarr_url: str | None = None
    radarr_api_key: str | None = None
    radarr_quality_profile: str | None = None
    tmdb_cache_time: str | None = None
    tmdb_cache_top_n: str | None = None
    tmdb_cache_top_actors: str | None = None
    mdblist_api_key: str | None = None
    tmdb_suggestions_seed_count: str | None = None
    mdblist_schedule_time: str | None = None      # NEW — HH:MM, default "04:00"
    mdblist_refetch_days: str | None = None        # NEW — int as string, default "90"


class SettingsUpdateRequest(BaseModel):
    tmdb_api_key: str | None = None
    radarr_url: str | None = None
    radarr_api_key: str | None = None
    radarr_quality_profile: str | None = None
    tmdb_cache_time: str | None = None
    tmdb_cache_top_n: str | None = None
    tmdb_cache_top_actors: str | None = None
    mdblist_api_key: str | None = None
    tmdb_suggestions_seed_count: str | None = None
    mdblist_schedule_time: str | None = None      # NEW
    mdblist_refetch_days: str | None = None        # NEW


class SettingsStatusResponse(BaseModel):
    tmdb_configured: bool
    migrated_from_env: bool = False


class ValidateRequest(BaseModel):
    tmdb_api_key: str | None = None
    radarr_url: str | None = None
    radarr_api_key: str | None = None
    radarr_quality_profile: str | None = None
    mdblist_api_key: str | None = None


class ServiceResult(BaseModel):
    ok: bool
    error: str | None = None
    warning: str | None = None


async def _resolve_key(submitted: str | None, db_key: str, db: AsyncSession) -> str | None:
    """If submitted value is a masked sentinel or None, read the real key from DB."""
    if submitted and not is_masked_sentinel(submitted):
        return submitted
    return await settings_service.get_setting(db, db_key)


async def _test_tmdb(key: str | None) -> ServiceResult:
    if not key:
        return ServiceResult(ok=False, error="TMDB API key is not configured")
    try:
        client = TMDBClient(api_key=key)
        try:
            await client.test_connection()
            return ServiceResult(ok=True)
        finally:
            await client.close()
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 401:
            return ServiceResult(ok=False, error="TMDB API key is invalid — check your Read Access Token")
        return ServiceResult(ok=False, error=f"TMDB returned status {exc.response.status_code}")
    except Exception as exc:
        return ServiceResult(ok=False, error=f"TMDB connection failed: {exc}")


async def _test_radarr(url: str | None, key: str | None, profile: str) -> ServiceResult:
    if not url:
        return ServiceResult(ok=False, error="Radarr URL is not configured")
    if not key:
        return ServiceResult(ok=False, error="Radarr API key is not configured")
    client = RadarrClient(base_url=url, api_key=key, quality_profile=profile)
    try:
        result = await client.test_connection()
        return ServiceResult(**result)
    finally:
        await client.close()


async def _test_mdblist(key: str | None) -> ServiceResult:
    if not key:
        return ServiceResult(ok=False, error="MDBList API key is not configured")
    result = await test_mdblist_connection(key)
    return ServiceResult(**result)


@router.post("/validate")
async def validate_all(body: ValidateRequest, db: AsyncSession = Depends(get_db)) -> dict[str, ServiceResult]:
    results: dict[str, ServiceResult] = {}
    # TMDB
    tmdb_key = await _resolve_key(body.tmdb_api_key, "tmdb_api_key", db)
    results["tmdb"] = await _test_tmdb(tmdb_key)
    # Radarr
    radarr_key = await _resolve_key(body.radarr_api_key, "radarr_api_key", db)
    radarr_url = body.radarr_url if body.radarr_url else await settings_service.get_setting(db, "radarr_url")
    radarr_profile = body.radarr_quality_profile if body.radarr_quality_profile else (await settings_service.get_setting(db, "radarr_quality_profile") or "HD+")
    results["radarr"] = await _test_radarr(radarr_url, radarr_key, radarr_profile)
    # MDBList
    mdblist_key = await _resolve_key(body.mdblist_api_key, "mdblist_api_key", db)
    results["mdblist"] = await _test_mdblist(mdblist_key)
    return results


@router.post("/validate/{service}")
async def validate_service(service: str, body: ValidateRequest, db: AsyncSession = Depends(get_db)) -> ServiceResult:
    if service == "tmdb":
        key = await _resolve_key(body.tmdb_api_key, "tmdb_api_key", db)
        return await _test_tmdb(key)
    elif service == "radarr":
        key = await _resolve_key(body.radarr_api_key, "radarr_api_key", db)
        url = body.radarr_url if body.radarr_url else await settings_service.get_setting(db, "radarr_url")
        profile = body.radarr_quality_profile if body.radarr_quality_profile else (await settings_service.get_setting(db, "radarr_quality_profile") or "HD+")
        return await _test_radarr(url, key, profile)
    elif service == "mdblist":
        key = await _resolve_key(body.mdblist_api_key, "mdblist_api_key", db)
        return await _test_mdblist(key)
    else:
        return ServiceResult(ok=False, error=f"Unknown service: {service}")


@router.get("", response_model=SettingsResponse)
async def get_settings(db: AsyncSession = Depends(get_db)) -> SettingsResponse:
    """Return all current settings with secret fields masked (per SEC-01)."""
    data = await settings_service.get_all_settings(db)
    masked = _mask_settings_response(data)
    return SettingsResponse(**{k: masked.get(k) for k in SettingsResponse.model_fields})


@router.put("", response_model=SettingsResponse)
async def update_settings(
    request: Request,
    body: SettingsUpdateRequest,
    db: AsyncSession = Depends(get_db),
) -> SettingsResponse:
    """Save updated settings. Skips masked sentinel values (per D-01 -- user did not change key)."""
    updates = {
        k: v
        for k, v in body.model_dump(exclude_none=True).items()
        if not is_masked_sentinel(v)
    }
    if updates:
        await settings_service.save_settings(db, updates)
        await db.commit()

    # If tmdb_api_key was updated, reinitialize the live TMDBClient on app.state
    if "tmdb_api_key" in updates:
        new_key = updates["tmdb_api_key"]
        old_client: TMDBClient = request.app.state.tmdb_client
        await old_client.close()
        request.app.state.tmdb_client = TMDBClient(api_key=new_key)
        register_secret(new_key)

    data = await settings_service.get_all_settings(db)
    masked = _mask_settings_response(data)
    return SettingsResponse(**{k: masked.get(k) for k in SettingsResponse.model_fields})


@router.get("/status", response_model=SettingsStatusResponse)
async def get_settings_status(db: AsyncSession = Depends(get_db)) -> SettingsStatusResponse:
    """Return configuration status flags."""
    configured = await settings_service.is_tmdb_configured(db)
    return SettingsStatusResponse(tmdb_configured=configured)


@router.get("/db-health")
async def get_db_health(db: AsyncSession = Depends(get_db)):
    """Return live DB row-level health stats and table sizes."""
    row_stats = await db.execute(text("""
        SELECT
          COUNT(*) AS total_movies,
          COUNT(*) FILTER (WHERE overview IS NULL OR overview = '') AS missing_overview,
          COUNT(*) FILTER (WHERE mpaa_rating IS NULL OR mpaa_rating = '') AS missing_mpaa,
          COUNT(*) FILTER (WHERE imdb_id IS NULL OR imdb_id = '') AS missing_imdb_id,
          COUNT(*) FILTER (WHERE imdb_rating IS NULL OR imdb_rating = 0) AS missing_imdb_rating,
          COUNT(*) FILTER (WHERE rt_score IS NULL OR rt_score = 0) AS missing_rt_score,
          COUNT(*) FILTER (WHERE mdblist_fetched_at IS NULL) AS never_mdblist_fetched
        FROM movies
    """))
    r = row_stats.mappings().one()

    total_actors_result = await db.execute(text("SELECT COUNT(*) FROM actors"))

    size_stats = await db.execute(text("""
        SELECT
          pg_size_pretty(pg_database_size(current_database())) AS total_db,
          pg_size_pretty(pg_total_relation_size('movies')) AS movies,
          pg_size_pretty(pg_total_relation_size('credits')) AS credits,
          pg_size_pretty(pg_total_relation_size('actors')) AS actors,
          pg_size_pretty(pg_total_relation_size('watch_events')) AS watch_events
    """))
    s = size_stats.mappings().one()

    return {
        "row_health": dict(r) | {"total_actors": total_actors_result.scalar()},
        "table_sizes": dict(s),
    }
