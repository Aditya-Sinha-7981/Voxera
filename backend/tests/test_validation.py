"""URL validation tests (API §3.1)."""
from __future__ import annotations

import pytest

from app.api.validation import UrlValidationError, validate_audio_url


@pytest.mark.parametrize(
    "url",
    [
        "https://example.com/audio.mp3",
        "http://example.com/audio.mp3",
        "https://example.com/path/to/rec.wav?token=abc",
    ],
)
def test_accepts_http_and_https(url: str) -> None:
    assert validate_audio_url(url) == url


def test_strips_whitespace() -> None:
    assert validate_audio_url("  https://x.com/a.mp3  ") == "https://x.com/a.mp3"


@pytest.mark.parametrize(
    "url",
    [
        "ftp://example.com/a.mp3",
        "file:///etc/passwd",
        "javascript:alert(1)",
    ],
)
def test_rejects_disallowed_scheme(url: str) -> None:
    with pytest.raises(UrlValidationError) as ei:
        validate_audio_url(url)
    assert ei.value.code == "INVALID_AUDIO_URL"


@pytest.mark.parametrize(
    "url",
    ["", "not-a-url", "https://", None, 123, [], {}],
)
def test_rejects_malformed(url) -> None:
    with pytest.raises(UrlValidationError):
        validate_audio_url(url)
