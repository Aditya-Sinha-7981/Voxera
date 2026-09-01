"""Model serialization tests — wire shapes match API.md exactly."""
from __future__ import annotations

import json
from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from app.models import (
    ActionItem,
    ActionStatus,
    ConversationAnalysis,
    ConversationType,
    CreateRecordingResponse,
    ImportantDetail,
    Priority,
    RecordingListItem,
    RecordingStatus,
    Segment,
    Sentiment,
    SentimentLabel,
    Transcript,
)


def test_create_recording_response_camel() -> None:
    r = CreateRecordingResponse(id="rec_x", status=RecordingStatus.PENDING)
    assert json.loads(r.model_dump_json(by_alias=True)) == {"id": "rec_x", "status": "pending"}


def test_list_item_camel_keys() -> None:
    item = RecordingListItem(
        id="rec_x",
        status=RecordingStatus.COMPLETED,
        title="AC complaint",
        conversation_type="complaint",
        sentiment="negative",
        created_at=datetime(2026, 8, 31, 10, 0, 0, tzinfo=timezone.utc),
    )
    # Wire shape per API §1.2: ISO 8601 UTC with `Z` suffix.
    expected_ts = "2026-08-31T10:00:00Z"
    dumped = json.loads(item.model_dump_json(by_alias=True))
    assert dumped["createdAt"] == expected_ts
    assert dumped["id"] == "rec_x"
    assert dumped["status"] == "completed"
    assert dumped["title"] == "AC complaint"
    assert dumped["conversationType"] == "complaint"
    assert dumped["sentiment"] == "negative"


def test_analysis_schema_validates() -> None:
    a = ConversationAnalysis(
        title="AC complaint",
        summary="Guest reported AC issue.",
        conversation_type=ConversationType.COMPLAINT,
        sentiment=Sentiment(label=SentimentLabel.NEGATIVE, score=0.87),
        key_points=["k"],
        complaints=["c"],
        requests=["r"],
        action_items=[
            ActionItem(
                action="Send maintenance.",
                department="maintenance",
                priority=Priority.HIGH,
                status=ActionStatus.PROMISED,
            )
        ],
        important_details=[ImportantDetail(key="room_number", value="203")],
        follow_up_required=True,
    )
    a.model_validate(a.model_dump())  # round-trip


def test_sentiment_score_clamped() -> None:
    with pytest.raises(ValidationError):
        Sentiment(label=SentimentLabel.POSITIVE, score=1.5)


def test_conversation_type_validates_against_enum() -> None:
    with pytest.raises(ValueError):
        ConversationType("not_a_real_type")


def test_recording_status_values_match_spec() -> None:
    expected = {
        "pending",
        "downloading",
        "transcribing",
        "analyzing",
        "saving",
        "completed",
        "failed",
    }
    assert {s.value for s in RecordingStatus} == expected


def test_segment_optional_fields() -> None:
    s = Segment(text="hi")  # speaker/role/start/end all optional
    assert s.speaker is None and s.start is None and s.text == "hi"


def test_transcript_defaults() -> None:
    t = Transcript()
    assert t.text == "" and t.segments == [] and t.language is None
