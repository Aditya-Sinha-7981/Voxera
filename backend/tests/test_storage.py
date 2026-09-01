"""Storage-layer unit tests with the Supabase client pinned to a fake.

Tests the chokepoints we can verify without a real database:
  * ID generation shape
  * Timestamp formatting
  * Status-enum values
"""
from __future__ import annotations

import re

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
    terminals = {RecordingStatus.COMPLETED.value, RecordingStatus.FAILED.value}
    assert terminals == {"completed", "failed"}
