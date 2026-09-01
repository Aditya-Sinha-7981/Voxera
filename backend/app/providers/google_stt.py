"""Phase 2 stub — real impl in Phase 3."""
from __future__ import annotations

from pathlib import Path

from app.models.transcript import Transcript
from app.providers.base import SpeechToTextProvider


class GoogleSTTProvider(SpeechToTextProvider):
    name = "google"

    def __init__(self, project: str = "", credentials_path: str = "") -> None:
        self._project = project
        self._credentials_path = credentials_path

    def transcribe(self, audio_path: Path) -> Transcript:
        return Transcript(language="unknown", text="", segments=[])
