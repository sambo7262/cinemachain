from __future__ import annotations

import logging

from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AppSettings
from app.settings import settings as env_settings

logger = logging.getLogger(__name__)

# Keys whose values are considered secrets (encrypted at rest)
_SECRET_KEYWORDS = ("key", "token", "password")

# Settings keys to migrate from .env on first startup
_ENV_KEYS_TO_MIGRATE = (
    "tmdb_api_key",
    "tmdb_base_url",
    "radarr_url",
    "radarr_api_key",
    "radarr_quality_profile",
    "tmdb_cache_time",
    "tmdb_cache_top_n",
    "tmdb_cache_top_actors",
)


def _get_fernet() -> Fernet | None:
    """Return a Fernet instance if encryption key is configured, else None."""
    key = env_settings.settings_encryption_key
    if key:
        return Fernet(key.encode() if isinstance(key, str) else key)
    return None


def encrypt_value(plaintext: str) -> str:
    """Encrypt plaintext if Fernet key is available; otherwise return as-is."""
    fernet = _get_fernet()
    if fernet is None:
        return plaintext
    return fernet.encrypt(plaintext.encode()).decode()


def decrypt_value(ciphertext: str) -> str:
    """Decrypt ciphertext if Fernet key is available; return raw value on failure."""
    fernet = _get_fernet()
    if fernet is None:
        return ciphertext
    try:
        return fernet.decrypt(ciphertext.encode()).decode()
    except (InvalidToken, Exception):
        # Fallback: value was stored as plaintext (e.g., before key was configured)
        return ciphertext


def _is_secret_key(key: str) -> bool:
    """Return True if the key name indicates a sensitive value."""
    key_lower = key.lower()
    return any(kw in key_lower for kw in _SECRET_KEYWORDS)


async def get_all_settings(db: AsyncSession) -> dict[str, str | None]:
    """Return all settings as a dict, decrypting secret values."""
    result = await db.execute(select(AppSettings))
    rows = result.scalars().all()
    out: dict[str, str | None] = {}
    for row in rows:
        if row.value is None:
            out[row.key] = None
        elif row.is_secret:
            out[row.key] = decrypt_value(row.value)
        else:
            out[row.key] = row.value
    return out


async def get_setting(db: AsyncSession, key: str) -> str | None:
    """Return a single setting value by key, decrypting if secret."""
    result = await db.execute(select(AppSettings).where(AppSettings.key == key))
    row = result.scalar_one_or_none()
    if row is None:
        return None
    if row.value is None:
        return None
    if row.is_secret:
        return decrypt_value(row.value)
    return row.value


async def save_settings(db: AsyncSession, settings_dict: dict[str, str | None]) -> None:
    """Upsert settings. Secret keys are encrypted before storage."""
    for key, value in settings_dict.items():
        is_secret = _is_secret_key(key)
        stored_value: str | None
        if value is None:
            stored_value = None
        elif is_secret:
            stored_value = encrypt_value(str(value))
        else:
            stored_value = str(value)

        # Upsert: fetch existing or create new
        result = await db.execute(select(AppSettings).where(AppSettings.key == key))
        row = result.scalar_one_or_none()
        if row is None:
            row = AppSettings(key=key, value=stored_value, is_secret=is_secret)
            db.add(row)
        else:
            row.value = stored_value
            row.is_secret = is_secret


async def is_tmdb_configured(db: AsyncSession) -> bool:
    """Return True if tmdb_api_key is present and non-empty in app_settings."""
    value = await get_setting(db, "tmdb_api_key")
    return bool(value)


async def migrate_env_to_db(db: AsyncSession) -> bool:
    """
    If app_settings table is empty, migrate settings from .env into the DB.
    Returns True if migration occurred.
    """
    result = await db.execute(select(AppSettings).limit(1))
    existing = result.scalar_one_or_none()
    if existing is not None:
        return False

    # Build dict from pydantic settings, with hardcoded default for tmdb_base_url
    migration_data: dict[str, str | None] = {
        "tmdb_base_url": "https://api.themoviedb.org/3",
    }
    for key in _ENV_KEYS_TO_MIGRATE:
        if key == "tmdb_base_url":
            continue  # already set above
        raw = getattr(env_settings, key, None)
        migration_data[key] = str(raw) if raw is not None else None

    await save_settings(db, migration_data)
    logger.info("Migrated %d settings from .env to database", len(migration_data))
    return True
