"""Temporary audio downloader (§9 + §9.1 + §9.2).

URL validation is split deliberately between routes (synchronous syntax+scheme)
and this module (real reachability). This module only runs inside the
processing task, never in a request handler.
"""
from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

import httpx

from app.config import get_settings


class DownloadError(Exception):
    """Raised when audio cannot be fetched/validated.

    Mapped by processing service to `INVALID_AUDIO` (API §9).
    """

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass(frozen=True)
class DownloadResult:
    temp_dir: Path  # `/tmp/voxa/<recording_id>/` — owner is the processing task.
    audio_path: Path


def extension_for(url: str, content_type: str | None) -> str:
    """Choose a file extension from URL path, falling back to Content-Type.

    Phase-2 decision (documented): simple known mapping. Unknown -> `.bin`.
    """
    path = urlparse(url).path.lower()
    for ext in (".mp3", ".wav", ".m4a", ".ogg", ".flac", ".webm", ".mp4"):
        if path.endswith(ext):
            return ext
    if content_type:
        ct = content_type.split(";", 1)[0].strip().lower()
        mapping = {
            "audio/mpeg": ".mp3",
            "audio/mp3": ".mp3",
            "audio/wav": ".wav",
            "audio/x-wav": ".wav",
            "audio/mp4": ".m4a",
            "audio/x-m4a": ".m4a",
            "audio/ogg": ".ogg",
            "audio/flac": ".flac",
            "audio/webm": ".webm",
        }
        if ct in mapping:
            return mapping[ct]
    return ".bin"


async def download_audio(recording_id: str, url: str) -> DownloadResult:
    """Stream the audio to a per-recording temp dir.

    Raises DownloadError on timeout, oversized content, non-audio content-type,
    or any other transport failure.
    """
    settings = get_settings()
    max_bytes = settings.max_audio_file_size_mb * 1024 * 1024

    base = Path(settings.temp_audio_dir)
    base.mkdir(parents=True, exist_ok=True)
    temp_dir = base / recording_id
    temp_dir.mkdir(parents=True, exist_ok=True)

    # Best-effort extension from URL; we'll rewrite once we see the response.
    audio_path = temp_dir / f"audio{extension_for(url, None)}"

    timeout = httpx.Timeout(
        connect=settings.download_connect_timeout_seconds,
        read=settings.download_total_timeout_seconds,
        write=settings.download_total_timeout_seconds,
        pool=settings.download_connect_timeout_seconds,
    )

    try:
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            try:
                async with client.stream("GET", url) as resp:
                    if resp.status_code >= 400:
                        raise DownloadError(
                            "INVALID_AUDIO",
                            f"The audio URL returned HTTP {resp.status_code}.",
                        )

                    content_length = resp.headers.get("content-length")
                    if content_length is not None:
                        try:
                            if int(content_length) > max_bytes:
                                raise DownloadError(
                                    "INVALID_AUDIO",
                                    "The audio file exceeds the maximum allowed size.",
                                )
                        except ValueError:
                            pass

                    content_type = resp.headers.get("content-type")
                    if content_type and not content_type.split(";", 1)[0].strip().lower().startswith("audio/"):
                        raise DownloadError(
                            "INVALID_AUDIO",
                            "The URL did not return an audio resource.",
                        )

                    # Rewrite file path with the real Content-Type hint.
                    final_path = temp_dir / f"audio{extension_for(url, content_type)}"
                    audio_path = final_path

                    written = 0
                    with audio_path.open("wb") as fh:
                        async for chunk in resp.aiter_bytes(chunk_size=64 * 1024):
                            written += len(chunk)
                            if written > max_bytes:
                                fh.close()
                                audio_path.unlink(missing_ok=True)
                                raise DownloadError(
                                    "INVALID_AUDIO",
                                    "The audio file exceeds the maximum allowed size.",
                                )
                            fh.write(chunk)
            except httpx.ConnectTimeout as exc:
                raise DownloadError(
                    "INVALID_AUDIO",
                    "Could not connect to the audio host.",
                ) from exc
            except httpx.ReadTimeout as exc:
                raise DownloadError(
                    "INVALID_AUDIO",
                    "The audio download timed out.",
                ) from exc
            except httpx.HTTPError as exc:
                raise DownloadError(
                    "INVALID_AUDIO",
                    "The audio URL could not be downloaded.",
                ) from exc
    except asyncio.TimeoutError as exc:
        raise DownloadError(
            "INVALID_AUDIO",
            "The audio download timed out.",
        ) from exc

    if audio_path.stat().st_size == 0:
        raise DownloadError("INVALID_AUDIO", "The downloaded audio is empty.")

    return DownloadResult(temp_dir=temp_dir, audio_path=audio_path)


def remove_temp_dir(temp_dir: Path) -> None:
    """Best-effort recursive delete (§10.2 / §10.3). Never raises."""
    import shutil

    try:
        shutil.rmtree(temp_dir, ignore_errors=True)
    except Exception:  # noqa: BLE001
        pass
