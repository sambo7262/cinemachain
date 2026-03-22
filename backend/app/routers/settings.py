from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.services import settings_service

router = APIRouter(prefix="/settings", tags=["settings"])


class SettingsResponse(BaseModel):
    tmdb_api_key: str | None = None
    tmdb_base_url: str | None = None
    radarr_url: str | None = None
    radarr_api_key: str | None = None
    radarr_quality_profile: str | None = None
    tmdb_cache_time: str | None = None
    tmdb_cache_top_n: str | None = None
    tmdb_cache_top_actors: str | None = None
    mdblist_api_key: str | None = None


class SettingsUpdateRequest(BaseModel):
    tmdb_api_key: str | None = None
    tmdb_base_url: str | None = None
    radarr_url: str | None = None
    radarr_api_key: str | None = None
    radarr_quality_profile: str | None = None
    tmdb_cache_time: str | None = None
    tmdb_cache_top_n: str | None = None
    tmdb_cache_top_actors: str | None = None
    mdblist_api_key: str | None = None


class SettingsStatusResponse(BaseModel):
    tmdb_configured: bool
    migrated_from_env: bool = False


@router.get("", response_model=SettingsResponse)
async def get_settings(db: AsyncSession = Depends(get_db)) -> SettingsResponse:
    """Return all current settings (decrypted)."""
    data = await settings_service.get_all_settings(db)
    return SettingsResponse(**{k: data.get(k) for k in SettingsResponse.model_fields})


@router.put("", response_model=SettingsResponse)
async def update_settings(
    body: SettingsUpdateRequest,
    db: AsyncSession = Depends(get_db),
) -> SettingsResponse:
    """Save updated settings to the database."""
    await settings_service.save_settings(db, body.model_dump(exclude_none=True))
    await db.commit()
    data = await settings_service.get_all_settings(db)
    return SettingsResponse(**{k: data.get(k) for k in SettingsResponse.model_fields})


@router.get("/status", response_model=SettingsStatusResponse)
async def get_settings_status(db: AsyncSession = Depends(get_db)) -> SettingsStatusResponse:
    """Return configuration status flags."""
    configured = await settings_service.is_tmdb_configured(db)
    return SettingsStatusResponse(tmdb_configured=configured)
