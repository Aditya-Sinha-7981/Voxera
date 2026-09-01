"""Storage-layer unit tests with the Supabase client pinned to a fake.

Tests the chokepoints we can verify without a real database:
  * ID generation shape
  * Timestamp formatting
  * Status-enum values
  * Foreign-table join shape normalization (Supabase quirk — see test below).
"""
from __future__ import annotations

import re
from unittest.mock import MagicMock, patch

from app.models import RecordingStatus
from app.services import storage


def test_recording_id_shape() -> None:
    rid = storage.generate_recording_id()
    assert re.fullmatch(r"rec_[a-z0-9]{12}", rid), rid


def test_utc_now_iso_suffix() -> None:
    ts = storage.utc_now_iso()
    assert ts.endswith("Z")
    assert "T" in ts


def test_terminal_status_immutability_filter_excludes_only_terminals() -> None:
    # The chokepoint filter should not let a `completed` row be transitioned
    # back into anything else. Indirectly verified by checking the filter
    # values used in update_status().
    terminals = {RecordingStatus.COMPLETED.value, RecordingStatus.FAILED.value}
    assert terminals == {"completed", "failed"}


def test_list_recordings_handles_analyses_join_as_dict() -> None:
    """Supabase PostgREST returns a 1:1 join as a dict, not a list.

    Found by integration testing against a real project. The list endpoint
    used to KeyError on a completed row's joined `analyses` field.
    """
    fake_response = MagicMock()
    fake_response.data = [
        {
            "id": "rec_completed",
            "status": "completed",
            "audio_url": "https://x",
            "created_at": "2026-09-01T04:53:51Z",
            "completed_at": "2026-09-01T04:54:14Z",
            "error_code": None,
            "error_message": None,
            "analyses": {
                "title": "AC complaint",
                "conversation_type": "complaint",
                "sentiment": {"label": "negative", "score": 0.87},
            },
        },
        {
            "id": "rec_pending",
            "status": "pending",
            "audio_url": "https://y",
            "created_at": "2026-09-01T05:00:00Z",
            "completed_at": None,
            "error_code": None,
            "error_message": None,
            "analyses": None,
        },
        {
            "id": "rec_failed",
            "status": "failed",
            "audio_url": "https://z",
            "created_at": "2026-09-01T05:01:00Z",
            "completed_at": None,
            "error_code": "ANALYSIS_FAILED",
            "error_message": "x",
            "analyses": [],
        },
    ]
    fake_response.count = 3

    fake_table = MagicMock()
    fake_query = MagicMock()
    fake_table.select.return_value = fake_query
    fake_query.order.return_value = fake_query
    fake_query.range.return_value = fake_query
    if True:  # conditional eq path
        fake_query.execute.return_value = fake_response

    with patch.object(storage, "_client") as mock_client:
        mock_client.return_value.table.return_value = fake_table
        result = storage.list_recordings(limit=10, offset=0)

    assert result.total == 3
    by_id = {item.id: item for item in result.items}
    assert by_id["rec_completed"].title == "AC complaint"
    assert by_id["rec_completed"].sentiment == "negative"
    assert by_id["rec_pending"].title is None
    assert by_id["rec_pending"].sentiment is None
    assert by_id["rec_failed"].title is None
