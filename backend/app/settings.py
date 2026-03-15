from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str
    tmdb_api_key: str
    plex_token: str
    plex_url: str
    radarr_url: str
    radarr_api_key: str
    sonarr_url: str
    sonarr_api_key: str

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
