"""Processing orchestration (§7.5 + §8 + §10).

`run_processing(recording_id)` is the seam called by:
  * the route handler (POST /api/v1/recordings)
  * the startup reconciliation sweep (§7.4)
  * the future DB-backed poller (deferred per ARCHITECTURE §7.1)

It owns the full lifecycle and guarantees temp-audio cleanup via try/finally
(§10.2). It does not know how it was invoked.
"""
from __future__ import annotations

import asyncio
import logging
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from app.models.analysis import ConversationAnalysis
from app.models.recording import RecordingStatus
from app.models.transcript import Transcript
from app.providers import get_gemini_analyzer, get_stt_provider
from app.providers.gemini import GeminiError, GeminiValidationFailure
from app.services import storage
from app.services.downloader import DownloadError, download_audio, remove_temp_dir

logger = logging.getLogger("voxera.processing")


class ProcessingFailure(Exception):
    """Internal-only failure representation. Carries the safe public error."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def _set(recording_id: str, status: RecordingStatus, **kw) -> None:
    """Transition the recording and log. Persistence failures are fatal."""
    try:
        storage.update_status(recording_id, status, **kw)
    except storage.StorageError as exc:
        logger.error(
            "persistence_failed recording_id=%s target=%s error=%s",
            recording_id, status.value, exc,
        )
        raise ProcessingFailure("PERSISTENCE_FAILED", "The result could not be saved.") from exc
    logger.info(
        "status recording_id=%s status=%s", recording_id, status.value,
    )


async def _transcribe(audio_path: Path) -> Transcript:
    """Run STT off the event loop (§7.2)."""
    provider = get_stt_provider()

    def _call() -> Transcript:
        return provider.transcribe(audio_path)

    try:
        return await asyncio.to_thread(_call)
    except Exception as exc:  # noqa: BLE001
        raise ProcessingFailure(
            "TRANSCRIPTION_FAILED",
            "The recording could not be transcribed.",
        ) from exc


async def _analyze(transcript: Transcript) -> ConversationAnalysis:
    """Run Gemini analysis off the event loop, with §17.1 retry semantics.

    The retry lives inside `analyze` itself (Phase 3): on first Pydantic failure
    it re-calls Gemini once with the validation error appended. After the retry
    we get either a valid `ConversationAnalysis` or a `GeminiValidationFailure`
    that maps to ANALYSIS_FAILED.
    """
    analyzer = get_gemini_analyzer()

    def _call(t: Transcript) -> ConversationAnalysis:
        return analyzer.analyze(t)

    try:
        return await asyncio.to_thread(_call, transcript)
    except GeminiValidationFailure as exc:
        logger.warning(
            "gemini_validation_failed_after_retry first=%s second=%s",
            exc.first_error, exc.second_error,
        )
        raise ProcessingFailure(
            "ANALYSIS_FAILED",
            "The conversation could not be analyzed.",
        ) from exc
    except GeminiError as exc:
        logger.error("gemini_error %s", exc)
        raise ProcessingFailure(
            "ANALYSIS_FAILED",
            "The conversation could not be analyzed.",
        ) from exc
    except Exception as exc:  # noqa: BLE001
        raise ProcessingFailure(
            "ANALYSIS_FAILED",
            "The conversation could not be analyzed.",
        ) from exc


async def run_processing(recording_id: str) -> None:
    """End-to-end: download → transcribe → analyze → persist → cleanup.

    Invariant: the temp directory is removed on every exit path. A recording
    is only marked `completed` after both transcript and analysis persist.
    """
    audio_path: Optional[Path] = None
    temp_dir: Optional[Path] = None

    try:
        # ---- downloading ----
        _set(recording_id, RecordingStatus.DOWNLOADING)
        recording = storage.get_recording_row(recording_id)
        if recording is None:
            # Already reaped by reconciliation — nothing to do.
            return
        audio_url = recording["audio_url"]

        try:
            dl = await download_audio(recording_id, audio_url)
            temp_dir = dl.temp_dir
            audio_path = dl.audio_path
        except DownloadError as exc:
            raise ProcessingFailure(exc.code, exc.message) from exc

        # ---- transcribing ----
        _set(recording_id, RecordingStatus.TRANSCRIBING)
        transcript = await _transcribe(audio_path)

        # ---- analyzing ----
        _set(recording_id, RecordingStatus.ANALYZING)
        analysis = await _analyze(transcript)

        # ---- saving ----
        _set(recording_id, RecordingStatus.SAVING)
        storage.save_transcript(recording_id, transcript)
        storage.save_analysis(recording_id, analysis)

        # ---- completed ----
        _set(recording_id, RecordingStatus.COMPLETED)

    except ProcessingFailure as pf:
        logger.warning(
            "processing_failed recording_id=%s code=%s message=%s",
            recording_id, pf.code, pf.message,
        )
        try:
            _set(
                recording_id,
                RecordingStatus.FAILED,
                error_code=pf.code,
                error_message=pf.message,
            )
        except ProcessingFailure:
            pass

    except Exception as exc:  # noqa: BLE001
        logger.error(
            "processing_unexpected recording_id=%s error=%s\n%s",
            recording_id, exc, traceback.format_exc(),
        )
        try:
            _set(
                recording_id,
                RecordingStatus.FAILED,
                error_code="PROCESSING_FAILED",
                error_message="The recording could not be processed.",
            )
        except ProcessingFailure:
            pass

    finally:
        if temp_dir is not None:
            remove_temp_dir(temp_dir)
