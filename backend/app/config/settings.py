from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Global application settings.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
        extra="ignore",
    )

    #
    # Application
    #
    app_name: str = Field(default="Investment OS")
    app_version: str = Field(default="0.1.0")
    app_env: str = Field(default="development")
    debug: bool = False

    #
    # API
    #
    host: str = "0.0.0.0"
    port: int = 8000

    #
    # Database
    #
    database_url: str

    #
    # Redis
    #
    redis_url: str

    #
    # Logging
    #
    log_level: str = "INFO"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
