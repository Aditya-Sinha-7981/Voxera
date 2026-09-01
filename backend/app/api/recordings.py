"""Recording routes (API §3-§11).

Handlers stay thin. They:
  1. Validate input (§3.1).
  2. Create a `pending` row.
  3. Delegate to the worker.
  4. Return.
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Query
from pydantic import ValidationError

from app.api.errors import api_error
from app.api.validation import UrlValidationError, validate_audio_url
from app.models.analysis import (
    ConversationAnalysis,
    ConversationType,
    Sentiment,
    SentimentLabel,
)
from app.models.recording import (
    CreateRecordingRequest,
    CreateRecordingResponse,
    RecordingDetail,
    RecordingError,
    RecordingList,
    RecordingListItem,
    RecordingStatus,
)
from app.models.transcript import Segment, Transcript
from app.services import storage
from app.workers.processor import schedule

router = APIRouter(prefix="/api/v1/recordings", tags=["recordings"])
logger = logging.getLogger("voxera.api.recordings")


@router.post("", status_code=202, response_model=CreateRecordingResponse)
async def create_recording(body: CreateRecordingRequest) -> CreateRecordingResponse:
    try:
        audio_url = validate_audio_url(body.audio_url)
    except UrlValidationError as exc:
        raise api_error(400, exc.code, exc.message) from exc

    try:
        created = storage.create_recording(audio_url)
    except storage.StorageError as exc:
        raise api_error(500, "PROCESSING_FAILED", "The recording could not be created.") from exc

    schedule(created.id)
    return created


@router.get("", response_model=RecordingList)
async def list_recordings(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    status: Optional[RecordingStatus] = Query(default=None),
) -> RecordingList:
    try:
        return storage.list_recordings(limit=limit, offset=offset, status=status)
    except storage.StorageError as exc:
        raise api_error(500, "PROCESSING_FAILED", "The recordings could not be listed.") from exc


@router.get("/{recording_id}", response_model=RecordingDetail)
async def get_recording(recording_id: str) -> RecordingDetail:
    try:
        row = storage.get_recording_row(recording_id)
    except storage.StorageError as exc:
        raise api_error(500, "PROCESSING_FAILED", "The recording could not be retrieved.") from exc
    if row is None:
        raise api_error(404, "RECORDING_NOT_FOUND", "The recording was not found.")

    status = RecordingStatus(row["status"])
    detail = RecordingDetail(
        id=row["id"],
        status=status,
        created_at=_parse_ts(row.get("created_at")),
    )

    if status is RecordingStatus.COMPLETED:
        detail.completed_at = _parse_ts(row.get("completed_at"))
        detail.transcript = _hydrate_transcript(recording_id)
        detail.analysis = _hydrate_analysis(recording_id)
    elif status is RecordingStatus.FAILED:
        detail.error = RecordingError(
            code=row.get("error_code") or "PROCESSING_FAILED",
            message=row.get("error_message") or "The recording could not be processed.",
        )
    return detail


# ---- helpers --------------------------------------------------------------

def _parse_ts(value) -> Optional[datetime]:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None


def _hydrate_transcript(recording_id: str) -> Optional[Transcript]:
    row = storage.get_transcript_row(recording_id)
    if row is None:
        return None
    segments = [
        Segment(
            speaker=s.get("speaker"),
            role=s.get("role"),
            start=s.get("start"),
            end=s.get("end"),
            text=s.get("text", ""),
        )
        for s in (row.get("segments") or [])
    ]
    return Transcript(language=row.get("language"), text=row.get("raw_text") or "", segments=segments)


def _hydrate_analysis(recording_id: str) -> Optional[ConversationAnalysis]:
    row = storage.get_analysis_row(recording_id)
    if row is None:
        return None
    try:
        sentiment_payload = row.get("sentiment") or {"label": "neutral", "score": 0.0}
        sentiment = Sentiment(
            label=SentimentLabel(sentiment_payload.get("label")),
            score=float(sentiment_payload.get("score", 0.0)),
        )
        return ConversationAnalysis(
            title=row.get("title") or "",
            summary=row.get("summary") or "",
            conversation_type=ConversationType(row.get("conversation_type") or "other"),
            sentiment=sentiment,
            key_points=list(row.get("key_points") or []),
            complaints=list(row.get("complaints") or []),
            requests=list(row.get("requests") or []),
            action_items=list(row.get("action_items") or []),
            important_details=list(row.get("important_details") or []),
            follow_up_required=bool(row.get("follow_up_required")),
        )
    except (ValidationError, ValueError):
        # Stored row should already match the schema; if not, surface as missing.
        return None
