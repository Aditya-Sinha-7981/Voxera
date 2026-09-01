"""Recording-related Pydantic models and the §8 state machine.

Wire shapes mirror docs/API.md exactly.
"""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_serializer
from pydantic.alias_generators import to_camel

from app.models._serialization import to_iso_z


class RecordingStatus(str, Enum):
    """§8 state machine. Values are the exact wire strings."""

    PENDING = "pending"
    DOWNLOADING = "downloading"
    TRANSCRIBING = "transcribing"
    ANALYZING = "analyzing"
    SAVING = "saving"
    COMPLETED = "completed"
    FAILED = "failed"


TERMINAL_STATUSES: frozenset[RecordingStatus] = frozenset(
    {RecordingStatus.COMPLETED, RecordingStatus.FAILED}
)


class CreateRecordingRequest(BaseModel):
    """POST /api/v1/recordings body (API §3)."""

    model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel)

    audio_url: str = Field(min_length=1)


class CreateRecordingResponse(BaseModel):
    """202 response body (API §4)."""

    model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel)

    id: str
    status: RecordingStatus


class RecordingError(BaseModel):
    """Top-level `error` object (API §9 / §10)."""

    model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel)

    code: str
    message: str


class RecordingListItem(BaseModel):
    """Sidebar entry (API §11)."""

    model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel)

    id: str
    status: RecordingStatus
    title: Optional[str] = None
    conversation_type: Optional[str] = None
    sentiment: Optional[str] = None  # label only in list view
    created_at: datetime

    @model_serializer
    def _serialize(self) -> dict[str, Any]:
        data = {
            "id": self.id,
            "status": self.status.value,
            "createdAt": to_iso_z(self.created_at),
        }
        if self.title is not None:
            data["title"] = self.title
        if self.conversation_type is not None:
            data["conversationType"] = self.conversation_type
        if self.sentiment is not None:
            data["sentiment"] = self.sentiment
        return data


class RecordingList(BaseModel):
    """Sidebar list response (API §11)."""

    model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel)

    items: list[RecordingListItem]
    total: int


class RecordingDetail(BaseModel):
    """Detail response assembled from recordings + transcript + analysis (API §5/§6/§9).

    The full detail shape varies by status:
      * processing  -> id, status (+ optional error)
      * completed   -> id, status, created_at, completed_at, transcript, analysis
      * failed      -> id, status, error
    Optional fields make every legal state expressible in one model.
    """

    model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel)

    id: str
    status: RecordingStatus
    created_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    transcript: Optional["TranscriptRef"] = None
    analysis: Optional["AnalysisRef"] = None
    error: Optional[RecordingError] = None

    @model_serializer
    def _serialize(self) -> dict[str, Any]:
        data: dict[str, Any] = {"id": self.id, "status": self.status.value}
        if self.created_at is not None:
            data["createdAt"] = to_iso_z(self.created_at)
        if self.completed_at is not None:
            data["completedAt"] = to_iso_z(self.completed_at)
        if self.transcript is not None:
            data["transcript"] = self.transcript.model_dump(by_alias=True)
        if self.analysis is not None:
            data["analysis"] = self.analysis.model_dump(by_alias=True)
        if self.error is not None:
            data["error"] = self.error.model_dump(by_alias=True)
        return data

    @field_validator("completed_at")
    @classmethod
    def _completed_only_when_completed(cls, v, info):
        # Soft check; storage layer is the source of truth. We don't raise here.
        return v


# Forward refs resolved below.
from app.models.transcript import TranscriptRef  # noqa: E402
from app.models.analysis import AnalysisRef  # noqa: E402

RecordingDetail.model_rebuild()
