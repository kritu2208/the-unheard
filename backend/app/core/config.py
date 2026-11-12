from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    app_name: str = "THE UNHEARD Dashboard API"
    app_version: str = "1.0.0-phase1"
    environment: str = "development"
    api_prefix: str = "/api"
    database_url: str = "sqlite:///./the_unheard_dashboard.db"
    cors_origins: List[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @property
    def is_sqlite(self) -> bool:
        """Return True when SQLite is the configured database dialect."""
        return self.database_url.startswith("sqlite")


@lru_cache
def get_settings() -> Settings:
    """Return cached application settings."""
    return Settings()

