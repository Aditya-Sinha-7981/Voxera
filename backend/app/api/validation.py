"""URL validation (synchronous, in-handler) (§3.1 + §9.1).

This module is intentionally narrow: it does NOT touch the network. It only
checks shape and scheme. Reachability is verified later, asynchronously,
during the `downloading` stage.
"""
from __future__ import annotations

from urllib.parse import urlparse


class UrlValidationError(ValueError):
    """Raised when `audio_url` is structurally invalid."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def validate_audio_url(url: object) -> str:
    """Validate `audio_url` synchronously. Returns the trimmed string on success."""
    if not isinstance(url, str):
        raise UrlValidationError("INVALID_AUDIO_URL", "The supplied audio URL is invalid.")
    candidate = url.strip()
    if not candidate:
        raise UrlValidationError("INVALID_AUDIO_URL", "The supplied audio URL is invalid.")
    try:
        parsed = urlparse(candidate)
    except Exception as exc:  # noqa: BLE001
        raise UrlValidationError("INVALID_AUDIO_URL", "The supplied audio URL is invalid.") from exc
    if parsed.scheme not in {"http", "https"}:
        raise UrlValidationError("INVALID_AUDIO_URL", "The audio URL must use http or https.")
    if not parsed.netloc:
        raise UrlValidationError("INVALID_AUDIO_URL", "The supplied audio URL is invalid.")
    return candidate
