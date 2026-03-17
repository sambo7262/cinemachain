from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str
    tmdb_api_key: str
    plex_token: str
    plex_url: str
    radarr_url: str
    radarr_api_key: str
    radarr_quality_profile: str = "HD+"
    sonarr_url: str
    sonarr_api_key: str
    tmdb_cache_top_n: int = 5000
    tmdb_cache_time: str = "03:00"

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
