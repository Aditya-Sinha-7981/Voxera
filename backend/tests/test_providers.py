"""Phase-3 provider unit tests.

These tests cover the *local* surface area of each provider —
language normalization, lazy model discipline, and Gemini's §17.1 retry
contract. Network-bound and model-bound tests are intentionally not in
this file; they belong in an integration suite with a recorded Gemini
fixture or a Whisper `tiny` model on a tiny audio clip.
"""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from pydantic import ValidationError

from app.models.analysis import ConversationAnalysis, Sentiment, SentimentLabel, ConversationType
from app.models.transcript import Segment, Transcript
from app.providers.gemini import GeminiAnalyzer, GeminiError, GeminiValidationFailure
from app.providers.google_stt import _detect_content_type, _normalize_language as g_normalize
from app.providers.whisper import _normalize_language as w_normalize


# ---------------------------------------------------------------------------
# Whisper — language normalization + non-fabrication
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "raw,expected",
    [
        ("en", "en"),
        ("hi", "hi"),
        ("EN", "en"),
        ("hi-en", "unknown"),  # Whisper never emits hyphenated; guard against drift.
        ("fr", "unknown"),
        (None, "unknown"),
        ("", "unknown"),
    ],
)
def test_whisper_normalize_language(raw, expected) -> None:
    assert w_normalize(raw) == expected


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("en-IN", "en"),
        ("hi-IN", "hi"),
        ("en", "en"),
        ("eng", "unknown"),
        (None, "unknown"),
    ],
)
def test_google_stt_normalize_language(raw, expected) -> None:
    assert g_normalize(raw) == expected


def test_whisper_lazy_model_loads_once() -> None:
    """`_ensure_model` must load the underlying model lazily and only once."""
    from app.providers.whisper import FasterWhisperProvider

    provider = FasterWhisperProvider(model_name="tiny")
    with patch("faster_whisper.WhisperModel") as MockModel:
        MockModel.return_value = MagicMock()
        provider._ensure_model()
        provider._ensure_model()
        provider._ensure_model()
        MockModel.assert_called_once()


def test_whisper_segments_never_fabricate_speaker_role() -> None:
    """Even if the underlying model returned speaker hints, we don't surface
    them — Whisper has no reliable diarization (§13)."""
    from app.providers.whisper import FasterWhisperProvider

    provider = FasterWhisperProvider(model_name="tiny")

    fake_model = MagicMock()
    fake_seg = MagicMock(start=0.0, end=1.0, text=" hello ")
    fake_iter = iter([fake_seg])
    fake_info = MagicMock(language="en")
    fake_model.transcribe.return_value = (fake_iter, fake_info)
    provider._model = fake_model

    out = provider.transcribe(Path("/tmp/anything.mp3"))
    assert isinstance(out, Transcript)
    assert out.language == "en"
    assert out.text == "hello"
    assert len(out.segments) == 1
    assert out.segments[0].speaker is None
    assert out.segments[0].role is None


# ---------------------------------------------------------------------------
# Gemini — §17.1 retry contract
# ---------------------------------------------------------------------------

def test_gemini_retry_on_first_validation_failure() -> None:
    """A first-attempt payload that fails Pydantic triggers a second call with
    a corrective prompt (§17.1). The second call's payload is validated."""
    analyzer = GeminiAnalyzer(api_key="fake-key", model="gemini-2.5-flash")

    bad_payload = {
        "title": "ok",
        "summary": "ok",
        "conversation_type": "complaint",
        "sentiment": {"label": "negative", "score": 1.5},  # invalid: >1.0
        "follow_up_required": True,
    }
    good_payload = {
        "title": "AC complaint",
        "summary": "Guest reported AC issue.",
        "conversation_type": "complaint",
        "sentiment": {"label": "negative", "score": 0.87},
        "key_points": ["k"],
        "complaints": ["c"],
        "requests": ["r"],
        "action_items": [
            {
                "action": "Send maintenance.",
                "department": "maintenance",
                "priority": "high",
                "status": "promised",
            }
        ],
        "important_details": [{"key": "room_number", "value": "203"}],
        "follow_up_required": True,
    }

    fake_client = MagicMock()
    fake_client.models.generate_content.side_effect = [
        MagicMock(text=json.dumps(bad_payload)),
        MagicMock(text=json.dumps(good_payload)),
    ]

    with patch.object(analyzer, "_client", fake_client):
        transcript = Transcript(language="en", text="hi", segments=[])
        result = analyzer.analyze(transcript)
        assert isinstance(result, ConversationAnalysis)
        assert result.title == "AC complaint"
        assert fake_client.models.generate_content.call_count == 2

        # Verify the second prompt contains a corrective hint.
        second_call = fake_client.models.generate_content.call_args_list[1]
        prompt = second_call.kwargs["contents"]
        assert "failed validation" in prompt.lower()


def test_gemini_double_failure_raises_validation_failure() -> None:
    analyzer = GeminiAnalyzer(api_key="fake-key", model="gemini-2.5-flash")
    invalid = {"title": "", "summary": "", "conversation_type": "complaint"}  # missing required

    fake_client = MagicMock()
    fake_client.models.generate_content.side_effect = [
        MagicMock(text=json.dumps(invalid)),
        MagicMock(text=json.dumps(invalid)),
    ]
    with patch.object(analyzer, "_client", fake_client):
        with pytest.raises(GeminiValidationFailure):
            analyzer.analyze(Transcript(text="hi", segments=[]))


def test_gemini_rejects_missing_api_key() -> None:
    with pytest.raises(GeminiError):
        GeminiAnalyzer(api_key="")


def test_gemini_propagates_transport_error() -> None:
    analyzer = GeminiAnalyzer(api_key="fake-key", model="gemini-2.5-flash")
    fake_client = MagicMock()
    fake_client.models.generate_content.side_effect = RuntimeError("boom")
    with patch.object(analyzer, "_client", fake_client):
        with pytest.raises(GeminiError):
            analyzer.analyze(Transcript(text="hi", segments=[]))


# ---------------------------------------------------------------------------
# Google STT — content-type mapping
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "filename,expected",
    [
        ("audio.mp3", "MP3"),
        ("audio.wav", "LINEAR16"),
        ("audio.flac", "FLAC"),
        ("audio.ogg", "OGG_OPUS"),
        ("audio.m4a", "ENCODED_WEBM_OPUS"),
        ("audio.webm", "WEBM_OPUS"),
        ("audio.unknown", "ENCODED_UNSPECIFIED"),
    ],
)
def test_google_stt_detect_content_type(filename: str, expected: str) -> None:
    assert _detect_content_type(Path(f"/tmp/{filename}")) == expected


def test_google_stt_requires_project() -> None:
    from app.providers.google_stt import GoogleSTTProvider

    with pytest.raises(ValueError):
        GoogleSTTProvider(project="")
