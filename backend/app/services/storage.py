"""Supabase storage layer.

Centralizes all DB access. The rest of the codebase never imports the
Supabase SDK directly. ID generation (`rec_<uuid>`) and timestamp formatting
(API §1.2) live here.
"""
from __future__ import annotations

import secrets
from datetime import datetime, timezone
from typing import Any, Optional

from supabase import Client, create_client

from app.config import get_settings
from app.models.analysis import ConversationAnalysis, ConversationType, SentimentLabel
from app.models.recording import (
    CreateRecordingResponse,
    RecordingError,
    RecordingList,
    RecordingListItem,
    RecordingStatus,
)
from app.models.transcript import Segment, Transcript


_REC_ID_ALPHABET = "abcdefghijklmnopqrstuvwxyz0123456789"
_MAX_LIST_LIMIT = 100
_DEFAULT_LIST_LIMIT = 20


class StorageError(RuntimeError):
    """Raised on persistence failure. Mapped to PERSISTENCE_FAILED by routes."""


def generate_recording_id() -> str:
    """`rec_` + 12-char URL-safe id (§9 / §18 — explicitly non-UUID column type)."""
    return "rec_" + "".join(secrets.choice(_REC_ID_ALPHABET) for _ in range(12))


def utc_now_iso() -> str:
    """ISO 8601 UTC with `Z` suffix (API §1.2)."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _client() -> Client:
    s = get_settings()
    if not s.supabase_url or not s.supabase_service_role_key:
        raise StorageError("Supabase configuration missing")
    return create_client(s.supabase_url, s.supabase_service_role_key)


# ---- Recording row --------------------------------------------------------

def create_recording(audio_url: str) -> CreateRecordingResponse:
    """Insert a new `pending` recording. Returns id + status (API §4)."""
    rid = generate_recording_id()
    row = {
        "id": rid,
        "audio_url": audio_url,
        "status": RecordingStatus.PENDING.value,
    }
    try:
        _client().table("recordings").insert(row).execute()
    except Exception as exc:  # noqa: BLE001
        raise StorageError(f"create_recording failed: {exc}") from exc
    return CreateRecordingResponse(id=rid, status=RecordingStatus.PENDING)


def update_status(
    recording_id: str,
    status: RecordingStatus,
    *,
    error_code: Optional[str] = None,
    error_message: Optional[str] = None,
) -> None:
    """Single chokepoint for state transitions.

    Terminal-state immutability (§8) is enforced here: once a recording is
    `completed` or `failed`, no further status writes succeed.
    """
    payload: dict[str, Any] = {"status": status.value}
    if error_code is not None:
        payload["error_code"] = error_code
    if error_message is not None:
        payload["error_message"] = error_message
    if status is RecordingStatus.COMPLETED:
        payload["completed_at"] = utc_now_iso()
    try:
        result = (
            _client()
            .table("recordings")
            .update(payload)
            .eq("id", recording_id)
            .not_.in_("status", [
                RecordingStatus.COMPLETED.value,
                RecordingStatus.FAILED.value,
            ])
            .execute()
        )
    except Exception as exc:  # noqa: BLE001
        raise StorageError(f"update_status failed: {exc}") from exc
    # `not_.in_` filter means empty result on terminal rows. That's the
    # intended outcome — the row already wins; the write must be a no-op.


def get_recording_row(recording_id: str) -> Optional[dict[str, Any]]:
    try:
        result = (
            _client()
            .table("recordings")
            .select("*")
            .eq("id", recording_id)
            .limit(1)
            .execute()
        )
    except Exception as exc:  # noqa: BLE001
        raise StorageError(f"get_recording_row failed: {exc}") from exc
    rows = result.data or []
    return rows[0] if rows else None


# ---- Transcript / analysis ------------------------------------------------

def save_transcript(recording_id: str, transcript: Transcript) -> None:
    row = {
        "id": generate_recording_id(),
        "recording_id": recording_id,
        "language": transcript.language,
        "raw_text": transcript.text,
        "segments": [s.model_dump(by_alias=True) for s in transcript.segments],
    }
    try:
        _client().table("transcripts").insert(row).execute()
    except Exception as exc:  # noqa: BLE001
        raise StorageError(f"save_transcript failed: {exc}") from exc


def save_analysis(recording_id: str, analysis: ConversationAnalysis) -> None:
    row = {
        "id": generate_recording_id(),
        "recording_id": recording_id,
        "title": analysis.title,
        "summary": analysis.summary,
        "conversation_type": analysis.conversation_type.value,
        "sentiment": analysis.sentiment.model_dump(by_alias=True),
        "key_points": list(analysis.key_points),
        "complaints": list(analysis.complaints),
        "requests": list(analysis.requests),
        "action_items": [a.model_dump(by_alias=True) for a in analysis.action_items],
        "important_details": [d.model_dump(by_alias=True) for d in analysis.important_details],
        "follow_up_required": analysis.follow_up_required,
    }
    try:
        _client().table("analyses").insert(row).execute()
    except Exception as exc:  # noqa: BLE001
        raise StorageError(f"save_analysis failed: {exc}") from exc


def get_transcript_row(recording_id: str) -> Optional[dict[str, Any]]:
    try:
        result = (
            _client()
            .table("transcripts")
            .select("*")
            .eq("recording_id", recording_id)
            .limit(1)
            .execute()
        )
    except Exception as exc:  # noqa: BLE001
        raise StorageError(f"get_transcript_row failed: {exc}") from exc
    rows = result.data or []
    return rows[0] if rows else None


def get_analysis_row(recording_id: str) -> Optional[dict[str, Any]]:
    try:
        result = (
            _client()
            .table("analyses")
            .select("*")
            .eq("recording_id", recording_id)
            .limit(1)
            .execute()
        )
    except Exception as exc:  # noqa: BLE001
        raise StorageError(f"get_analysis_row failed: {exc}") from exc
    rows = result.data or []
    return rows[0] if rows else None


# ---- List -----------------------------------------------------------------

def list_recordings(
    limit: int = _DEFAULT_LIST_LIMIT,
    offset: int = 0,
    status: Optional[RecordingStatus] = None,
) -> RecordingList:
    limit = max(1, min(limit, _MAX_LIST_LIMIT))
    offset = max(0, offset)
    try:
        query = (
            _client()
            .table("recordings")
            .select(
                "id, status, audio_url, created_at, completed_at, "
                "error_code, error_message, analyses(title, conversation_type, sentiment)",
                count="exact",
            )
            .order("created_at", desc=True)
            .range(offset, offset + limit - 1)
        )
        if status is not None:
            query = query.eq("status", status.value)
        result = query.execute()
    except Exception as exc:  # noqa: BLE001
        raise StorageError(f"list_recordings failed: {exc}") from exc

    items: list[RecordingListItem] = []
    for row in result.data or []:
        # Supabase PostgREST can return a Foreign-Table join as a dict, a list
        # of dicts, or null depending on cardinality. Normalize all three.
        raw_analysis = row.get("analyses")
        if isinstance(raw_analysis, list):
            analysis = raw_analysis[0] if raw_analysis else None
        elif isinstance(raw_analysis, dict):
            analysis = raw_analysis
        else:
            analysis = None
        sentiment_label = None
        if analysis and analysis.get("sentiment"):
            sentiment_label = analysis["sentiment"].get("label")
        items.append(
            RecordingListItem(
                id=row["id"],
                status=RecordingStatus(row["status"]),
                title=(analysis or {}).get("title"),
                conversation_type=(analysis or {}).get("conversation_type"),
                sentiment=sentiment_label,
                created_at=row["created_at"],
            )
        )
    total = getattr(result, "count", None) or len(items)
    return RecordingList(items=items, total=total)


# ---- Reconciliation (§7.4) -----------------------------------------------

_NON_TERMINAL_STATUSES = [
    RecordingStatus.PENDING.value,
    RecordingStatus.DOWNLOADING.value,
    RecordingStatus.TRANSCRIBING.value,
    RecordingStatus.ANALYZING.value,
    RecordingStatus.SAVING.value,
]


def find_stale_non_terminal(grace_period_seconds: int) -> list[str]:
    """Return ids of recordings stuck in non-terminal states past the grace period (§7.4)."""
    from datetime import datetime, timedelta, timezone

    cutoff = (
        datetime.now(timezone.utc) - timedelta(seconds=grace_period_seconds)
    ).isoformat()
    try:
        result = (
            _client()
            .table("recordings")
            .select("id, status")
            .in_("status", _NON_TERMINAL_STATUSES)
            .lt("created_at", cutoff)
            .execute()
        )
    except Exception as exc:  # noqa: BLE001
        raise StorageError(f"find_stale_non_terminal failed: {exc}") from exc
    return [row["id"] for row in result.data or []]


def mark_interrupted(recording_id: str) -> None:
    """Mark a stale recording as `failed` with the INTERRUPTED safe error (§7.4)."""
    update_status(
        recording_id,
        RecordingStatus.FAILED,
        error_code="INTERRUPTED",
        error_message="Processing was interrupted and did not complete.",
    )
