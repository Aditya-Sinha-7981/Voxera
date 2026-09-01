"""Pydantic-settings configuration loader.

Authoritative spec: docs/ARCHITECTURE.md §20.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration loaded from environment / `.env`."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ---- Application ----
    frontend_url: str = Field(
        default="http://localhost:3000",
        description="Origin allowed by CORS. No wildcard in production.",
    )

    # ---- Processing ----
    max_concurrent_jobs: int = Field(default=2, ge=1)
    max_audio_file_size_mb: int = Field(default=100, ge=1)
    download_connect_timeout_seconds: int = Field(default=10, ge=1)
    download_total_timeout_seconds: int = Field(default=60, ge=1)
    reconciliation_grace_period_seconds: int = Field(default=120, ge=0)

    temp_audio_dir: Path = Field(default=Path("/tmp/voxa"))

    # ---- STT ----
    stt_provider: str = Field(
        default="whisper",
        description="Either 'whisper' or 'google'. Factory in providers/__init__.py.",
    )
    whisper_model: str = Field(default="small")

    # ---- Google STT (only required when stt_provider == 'google') ----
    google_cloud_project: str = Field(default="")
    google_application_credentials: str = Field(default="")

    # ---- Gemini ----
    gemini_api_key: str = Field(default="")
    gemini_model: str = Field(default="gemini-2.5-flash")

    # ---- Database ----
    supabase_url: str = Field(default="")
    supabase_service_role_key: str = Field(default="")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Cached settings accessor. Overridable in tests."""
    return Settings()
