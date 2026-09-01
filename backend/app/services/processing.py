"""Phase 2 stub processing.py — real impl in Phase 3."""
from __future__ import annotations

import asyncio
import logging
import traceback
from pathlib import Path
from typing import Optional

from app.models.recording import RecordingStatus
from app.models.transcript import Transcript
from app.providers import get_gemini_analyzer, get_stt_provider
from app.services import storage
from app.services.downloader import DownloadError, download_audio, remove_temp_dir

logger = logging.getLogger("voxera.processing")


class ProcessingFailure(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def _set(recording_id: str, status: RecordingStatus, **kw) -> None:
    try:
        storage.update_status(recording_id, status, **kw)
    except storage.StorageError as exc:
        raise ProcessingFailure("PERSISTENCE_FAILED", "The result could not be saved.") from exc
    logger.info("status recording_id=%s status=%s", recording_id, status.value)


async def _transcribe(audio_path: Path) -> Transcript:
    provider = get_stt_provider()

    def _call() -> Transcript:
        return provider.transcribe(audio_path)

    try:
        return await asyncio.to_thread(_call)
    except Exception as exc:  # noqa: BLE001
        raise ProcessingFailure("TRANSCRIPTION_FAILED", "The recording could not be transcribed.") from exc


async def _analyze(transcript: Transcript):  # type: ignore[no-untyped-def]
    analyzer = get_gemini_analyzer()

    def _call_once(t: Transcript):  # type: ignore[no-untyped-def]
        return analyzer.analyze(t)

    try:
        result = await asyncio.to_thread(_call_once, transcript)
        return result
    except Exception as exc:  # noqa: BLE001
        raise ProcessingFailure("ANALYSIS_FAILED", "The conversation could not be analyzed.") from exc


async def run_processing(recording_id: str) -> None:
    audio_path: Optional[Path] = None
    temp_dir: Optional[Path] = None

    try:
        _set(recording_id, RecordingStatus.DOWNLOADING)
        recording = storage.get_recording_row(recording_id)
        if recording is None:
            return
        audio_url = recording["audio_url"]

        try:
            dl = await download_audio(recording_id, audio_url)
            temp_dir = dl.temp_dir
            audio_path = dl.audio_path
        except DownloadError as exc:
            raise ProcessingFailure(exc.code, exc.message) from exc

        _set(recording_id, RecordingStatus.TRANSCRIBING)
        transcript = await _transcribe(audio_path)

        _set(recording_id, RecordingStatus.ANALYZING)
        analysis = await _analyze(transcript)

        _set(recording_id, RecordingStatus.SAVING)
        storage.save_transcript(recording_id, transcript)
        storage.save_analysis(recording_id, analysis)

        _set(recording_id, RecordingStatus.COMPLETED)

    except ProcessingFailure as pf:
        try:
            _set(recording_id, RecordingStatus.FAILED, error_code=pf.code, error_message=pf.message)
        except ProcessingFailure:
            pass
    except Exception as exc:  # noqa: BLE001
        logger.error("processing_unexpected recording_id=%s error=%s\n%s", recording_id, exc, traceback.format_exc())
        try:
            _set(recording_id, RecordingStatus.FAILED, error_code="PROCESSING_FAILED",
                 error_message="The recording could not be processed.")
        except ProcessingFailure:
            pass
    finally:
        if temp_dir is not None:
            remove_temp_dir(temp_dir)
