"""Google Cloud Speech-to-Text provider.

Mirrors the Faster-Whisper provider's normalized-transcript contract (§12).
Speakers are not identified by Google STT by default — we request diarization
when available (up to 2 speakers for the hotel/guest conversation pattern,
per §1). Speaker *roles* (guest vs hotel_staff) are still left null here —
Gemini is responsible for inferring roles from context (§13).
"""
from __future__ import annotations

import logging
import os
from pathlib import Path

from app.models.transcript import Segment, Transcript
from app.providers.base import SpeechToTextProvider

logger = logging.getLogger("voxera.providers.google_stt")


_PRIMARY_LANGS = {"en", "hi"}


def _normalize_language(code: Optional[str]) -> str:
    if not code:
        return "unknown"
    c = code.lower()
    # BCP-47 like "en-IN" -> "en".
    primary = c.split("-", 1)[0]
    return primary if primary in _PRIMARY_LANGS else "unknown"


def _detect_content_type(audio_path: Path) -> str:
    """Map a temp-file extension to a Google STT `Encoding` enum value.

    The downloader writes the extension based on the URL path / Content-Type
    header, so this lookup is reliable enough for the MVP.
    """
    ext = audio_path.suffix.lower()
    return {
        ".mp3": "MP3",
        ".wav": "LINEAR16",
        ".flac": "FLAC",
        ".ogg": "OGG_OPUS",
        ".m4a": "ENCODED_WEBM_OPUS",  # closest cross-format option
        ".webm": "WEBM_OPUS",
        ".mp4": "ENCODED_WEBM_OPUS",
    }.get(ext, "ENCODED_UNSPECIFIED")


class GoogleSTTProvider(SpeechToTextProvider):
    """Real Google Cloud Speech-to-Text provider."""

    name = "google"

    def __init__(self, project: str = "", credentials_path: str = "") -> None:
        if not project:
            raise ValueError(
                "GOOGLE_CLOUD_PROJECT is required when STT_PROVIDER=google."
            )
        if credentials_path:
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = credentials_path
        self._project = project
        self._client = None  # lazy

    def _ensure_client(self):
        if self._client is None:
            from google.cloud import speech

            logger.info("initializing_google_stt_client project=%s", self._project)
            self._client = speech.SpeechClient()
        return self._client

    def transcribe(self, audio_path: Path) -> Transcript:
        from google.cloud import speech

        client = self._ensure_client()

        with audio_path.open("rb") as fh:
            content = fh.read()

        # Diarization hints at 2 speakers (the documented hotel-conversation
        # pattern — ARCHITECTURE §1). Adjust if your traffic shows otherwise.
        diarization = speech.SpeakerDiarizationConfig(
            enable_speaker_diarization=True,
            min_speaker_count=2,
            max_speaker_count=2,
        )
        config = speech.RecognitionConfig(
            encoding=getattr(speech.RecognitionConfig.AudioEncoding, _detect_content_type(audio_path)),
            language_code="en-IN",  # covers both English and (broadly) Hindi-English in India.
            enable_word_time_offsets=True,
            diarization_config=diarization,
            model="latest_long",
        )
        audio = speech.RecognitionAudio(content=content)

        response = client.recognize(config=config, audio=audio)

        segments: list[Segment] = []
        text_parts: list[str] = []
        detected_language: Optional[str] = None
        for result in response.results:
            alternative = result.alternatives[0]
            text_parts.append(alternative.transcript.strip())
            detected_language = (
                detected_language or getattr(result, "language_code", None)
            )

            # Reconstruct speaker segments from word-level info.
            words = alternative.words or []
            current_speaker = None
            current_text: list[str] = []
            current_start = None
            current_end = None

            def _flush() -> None:
                if not current_text:
                    return
                text = " ".join(current_text).strip()
                if text:
                    segments.append(
                        Segment(
                            speaker=f"Speaker {current_speaker}"
                            if current_speaker is not None
                            else None,
                            role=None,
                            start=current_start,
                            end=current_end,
                            text=text,
                        )
                    )

            for w in words:
                tag = getattr(w, "speaker_tag", 0) or 0
                start = w.start_time.total_seconds() if w.start_time else None
                end = w.end_time.total_seconds() if w.end_time else None
                if tag != current_speaker:
                    _flush()
                    current_speaker = tag
                    current_text = [w.word]
                    current_start = start
                    current_end = end
                else:
                    current_text.append(w.word)
                    if end is not None:
                        current_end = end
            _flush()

        return Transcript(
            language=_normalize_language(detected_language),
            text=" ".join(text_parts).strip(),
            segments=segments,
        )
