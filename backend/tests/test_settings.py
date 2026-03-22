"""
INFRA-02: All API keys and config are managed via .env — no credentials baked into images.
Settings module must load from environment and raise on missing required keys.
Wave 1 (Plan 03) implements app/settings.py. This test becomes green after Plan 03 executes.
"""
import pytest
import os


def test_settings_load_from_environment(monkeypatch):
    """Settings must load all required keys from environment variables."""
    # Provide placeholder values matching .env.example
    required_vars = {
        "DATABASE_URL": "postgresql+asyncpg://cinema:changeme@localhost:5432/cinemachain",
        "TMDB_API_KEY": "test_tmdb_key",
        "PLEX_TOKEN": "test_plex_token",
        "PLEX_URL": "http://192.168.1.1:32400",
        "RADARR_URL": "http://192.168.1.1:7878",
        "RADARR_API_KEY": "test_radarr_key",
        "SONARR_URL": "http://192.168.1.1:8989",
        "SONARR_API_KEY": "test_sonarr_key",
    }
    for k, v in required_vars.items():
        monkeypatch.setenv(k, v)

    try:
        # Force reimport so monkeypatched env is read fresh
        import importlib
        import app.settings as settings_module
        importlib.reload(settings_module)
        s = settings_module.settings
        assert s.database_url.startswith("postgresql")
        assert s.tmdb_api_key == "test_tmdb_key"
    except ImportError:
        pytest.skip("app.settings not yet implemented — Wave 1 will create it")


def test_required_env_vars_documented():
    """Verify .env.example documents all required keys (committed to repo)."""
    import pathlib
    env_example = pathlib.Path("backend/.env.example")
    if not env_example.exists():
        env_example = pathlib.Path(".env.example")
    if not env_example.exists():
        pytest.skip(".env.example not yet created — Wave 1 Plan 02 will create it")
    content = env_example.read_text()
    required_keys = ["DB_PASSWORD", "TMDB_API_KEY", "PLEX_TOKEN", "RADARR_API_KEY", "SONARR_API_KEY", "TS_AUTHKEY", "PUID", "PGID"]
    for key in required_keys:
        assert key in content, f"Missing required key in .env.example: {key}"


# ---------------------------------------------------------------------------
# Phase 6 Wave 0 stubs — RED phase (fail until Plan 01 implements settings service)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_db_overrides_env(client):
    """ITEM-6: DB-stored setting takes precedence over .env value after startup migration."""
    # Stub: will fail until Plan 01 implements settings service + router
    # GET /settings should return values (either from DB or migrated from .env)
    resp = await client.get("/api/settings")
    assert resp.status_code == 200, f"GET /settings returned {resp.status_code} — settings router may not exist"
    data = resp.json()
    assert "tmdb_api_key" in data, "Settings response missing tmdb_api_key field"

    # PUT a new value
    put_resp = await client.put("/api/settings", json={"tmdb_api_key": "new_test_key_override"})
    assert put_resp.status_code == 200, f"PUT /settings returned {put_resp.status_code}"

    # GET again — should reflect the DB-stored override
    resp2 = await client.get("/api/settings")
    assert resp2.status_code == 200
    assert resp2.json()["tmdb_api_key"] == "new_test_key_override", "DB setting did not override .env value"
