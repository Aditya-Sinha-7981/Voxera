"""Downloader extension-selection unit tests."""
from __future__ import annotations

import pytest

from app.services.downloader import extension_for


@pytest.mark.parametrize(
    "url,ct,expected",
    [
        ("https://x.com/a.mp3", None, ".mp3"),
        ("https://x.com/a.WAV", None, ".wav"),
        ("https://x.com/x?y=1", "audio/mpeg", ".mp3"),
        ("https://x.com/x", "audio/wav", ".wav"),
        ("https://x.com/x", "audio/x-m4a", ".m4a"),
        ("https://x.com/x", "audio/ogg; codecs=opus", ".ogg"),
        ("https://x.com/x", "video/mp4", ".bin"),
        ("https://x.com/x", None, ".bin"),
    ],
)
def test_extension_for(url, ct, expected) -> None:
    assert extension_for(url, ct) == expected
