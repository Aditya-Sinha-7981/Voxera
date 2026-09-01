"""Phase 2 stub — real impl in Phase 3."""
from __future__ import annotations

from pathlib import Path

from app.models.transcript import Transcript
from app.providers.base import SpeechToTextProvider


class FasterWhisperProvider(SpeechToTextProvider):
    name = "whisper"

    def __init__(self, model_name: str = "small") -> None:
        self._model_name = model_name

    def transcribe(self, audio_path: Path) -> Transcript:
        return Transcript(language="unknown", text="", segments=[])
