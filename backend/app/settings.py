from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str
    tmdb_api_key: str
    radarr_url: str
    radarr_api_key: str
    radarr_quality_profile: str = "HD+"
    tmdb_cache_top_n: int = 5000
    tmdb_cache_time: str = "03:00"
    tmdb_cache_run_on_startup: bool = False
    tmdb_cache_top_actors: int = 1500
    settings_encryption_key: str = ""

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
