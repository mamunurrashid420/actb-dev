"""Application configuration using pydantic-settings."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=(".env", ".env.local"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # API Settings
    api_title: str = "actBI API"
    api_version: str = "0.1.0"
    debug: bool = False

    # Supabase Settings (optional - only needed for non-playground routes)
    supabase_url: str | None = None
    supabase_anon_key: str | None = None
    supabase_service_role_key: str | None = None
    supabase_jwt_audience: str = "authenticated"
    supabase_jwt_issuer: str | None = None
    supabase_jwt_leeway_seconds: int = 10
    supabase_jwt_secret: str | None = None

    # App Security
    app_kms_key: str | None = None

    # Storage Settings
    storage_backend: str = "supabase"
    storage_bucket: str = "tenant-assets"
    storage_signed_url_ttl_seconds: int = 3600

    # CORS Settings (includes port 3003 for chartviz)
    cors_origins: list[str] = [
        "http://localhost:3000",
        "http://localhost:3001",
        "http://localhost:3003",
    ]

    # Playground (set PLAYGROUND=on to enable dev-only playground routes)
    playground: bool = False


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
