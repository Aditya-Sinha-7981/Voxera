"""Speech-to-text provider abstraction (§11)."""
from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from app.models.transcript import Transcript


class SpeechToTextProvider(ABC):
    """All STT implementations conform to this interface."""

    name: str = "abstract"

    @abstractmethod
    def transcribe(self, audio_path: Path) -> Transcript:
        """Transcribe `audio_path` and return a normalized Transcript.

        Implementations MUST NOT block the asyncio event loop. CPU-bound
        providers (Whisper) should be invoked via `asyncio.to_thread` by the
        caller (§7.2).
        """
        raise NotImplementedError
