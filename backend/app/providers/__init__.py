"""Phase 2 stub providers factory — no real API key required."""
from __future__ import annotations

from functools import lru_cache

from app.config import get_settings
from app.providers.base import SpeechToTextProvider
from app.providers.gemini import GeminiAnalyzer
from app.providers.google_stt import GoogleSTTProvider
from app.providers.whisper import FasterWhisperProvider


def get_stt_provider() -> SpeechToTextProvider:
    settings = get_settings()
    provider = (settings.stt_provider or "whisper").lower()
    if provider == "whisper":
        return FasterWhisperProvider(model_name=settings.whisper_model)
    if provider == "google":
        return GoogleSTTProvider(
            project=settings.google_cloud_project,
            credentials_path=settings.google_application_credentials,
        )
    raise ValueError(f"Unknown STT_PROVIDER: {settings.stt_provider!r}")


@lru_cache(maxsize=1)
def get_gemini_analyzer() -> GeminiAnalyzer:
    settings = get_settings()
    return GeminiAnalyzer(api_key=settings.gemini_api_key, model=settings.gemini_model)
