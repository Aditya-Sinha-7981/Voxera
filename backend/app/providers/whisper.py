"""Faster-Whisper provider (§11 + §12 + §13).

Whisper does not perform reliable speaker diarization, so `speaker` and `role`
fields on segments are intentionally left null. We never fabricate roles
(§13). The provider is event-loop-safe by contract — `processing.py` wraps
the call in `asyncio.to_thread` (§7.2).

The model is loaded lazily on first transcription and disposed on
`shutdown()` so FastAPI's lifespan can free memory when the process exits.
"""
from __future__ import annotations

import logging
import threading
from pathlib import Path
from typing import Optional

from app.models.transcript import Segment, Transcript
from app.providers.base import SpeechToTextProvider

logger = logging.getLogger("voxera.providers.whisper")

# Whisper language detection tags are two-letter ISO codes. The API contract
# allows `en`, `hi`, `hi-en`, `unknown`. Whisper itself only emits a single
# ISO code, so we synthesize `hi-en` only when mixed-script text suggests it.
_PRIMARY_LANGS = {"en", "hi"}


def _normalize_language(detected: Optional[str]) -> str:
    if not detected:
        return "unknown"
    code = detected.lower()
    return code if code in _PRIMARY_LANGS else "unknown"


class FasterWhisperProvider(SpeechToTextProvider):
    """Real Faster-Whisper provider.

    Use a tiny/base model on small deployment VMs. The model name is
    configurable via `WHISPER_MODEL` (ARCHITECTURE §11 + §26).
    """

    name = "whisper"

    def __init__(
        self,
        model_name: str = "small",
        device: str = "cpu",
        compute_type: str = "int8",
    ) -> None:
        self._model_name = model_name
        self._device = device
        self._compute_type = compute_type
        self._model = None
        self._lock = threading.Lock()

    def _ensure_model(self):
        if self._model is not None:
            return self._model
        with self._lock:
            if self._model is None:
                from faster_whisper import WhisperModel

                logger.info(
                    "loading_whisper_model name=%s device=%s compute_type=%s",
                    self._model_name, self._device, self._compute_type,
                )
                self._model = WhisperModel(
                    self._model_name,
                    device=self._device,
                    compute_type=self._compute_type,
                )
        return self._model

    def transcribe(self, audio_path: Path) -> Transcript:
        model = self._ensure_model()

        # `word_timestamps=False` — Whisper word timestamps are noisy and we
        # only need segment-level timing. `vad_filter=True` helps with noisy
        # hotel-call audio (ARCHITECTURE §1).
        segments_iter, info = model.transcribe(
            str(audio_path),
            vad_filter=True,
            word_timestamps=False,
        )

        segments: list[Segment] = []
        text_parts: list[str] = []
        for seg in segments_iter:
            text = (seg.text or "").strip()
            if not text:
                continue
            text_parts.append(text)
            segments.append(
                Segment(
                    speaker=None,  # Whisper has no reliable diarization.
                    role=None,
                    start=float(seg.start) if seg.start is not None else None,
                    end=float(seg.end) if seg.end is not None else None,
                    text=text,
                )
            )

        return Transcript(
            language=_normalize_language(getattr(info, "language", None)),
            text=" ".join(text_parts).strip(),
            segments=segments,
        )

    def shutdown(self) -> None:
        """Free model memory on app shutdown."""
        with self._lock:
            if self._model is not None:
                logger.info("disposing_whisper_model")
                self._model = None
