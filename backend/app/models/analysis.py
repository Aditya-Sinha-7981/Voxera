"""ConversationAnalysis — required analysis fields (§8 + §16).

This single Pydantic model serves three roles:
  1. Wire shape for API §6 / §8.
  2. Output validation target for Gemini (§15, §17).
  3. Storage shape for the `analyses` table.
"""
from __future__ import annotations

from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator
from pydantic.alias_generators import to_camel


# ---- Allowed enums (API §8 / §16) -----------------------------------------

class ConversationType(str, Enum):
    BOOKING = "booking"
    COMPLAINT = "complaint"
    INQUIRY = "inquiry"
    CANCELLATION = "cancellation"
    CHECK_IN = "check_in"
    CHECK_OUT = "check_out"
    MAINTENANCE = "maintenance"
    REQUEST = "request"
    GENERAL = "general"
    OTHER = "other"


class SentimentLabel(str, Enum):
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"


class Priority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ActionStatus(str, Enum):
    REQUESTED = "requested"
    PROMISED = "promised"
    COMPLETED = "completed"
    UNKNOWN = "unknown"


# ---- Composite objects ---------------------------------------------------

class Sentiment(BaseModel):
    model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel)

    label: SentimentLabel
    score: float = Field(ge=0.0, le=1.0)


class ActionItem(BaseModel):
    model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel)

    action: str
    department: Optional[str] = None
    priority: Priority
    status: ActionStatus


class ImportantDetail(BaseModel):
    """Loose shape for explicitly-mentioned operational facts.

    The architecture (§16) lists possible keys: booking reference, room number,
    dates, times, requirements. Gemini is told not to invent missing values.
    We keep this as a flexible dict to allow heterogeneous detail entries
    without forcing every record to carry every key.
    """

    model_config = ConfigDict(extra="allow")

    key: str
    value: str


class ConversationAnalysis(BaseModel):
    """Full analysis object (API §8)."""

    model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel)

    title: str
    summary: str
    conversation_type: ConversationType
    sentiment: Sentiment
    key_points: List[str] = Field(default_factory=list)
    complaints: List[str] = Field(default_factory=list)
    requests: List[str] = Field(default_factory=list)
    action_items: List[ActionItem] = Field(default_factory=list)
    important_details: List[ImportantDetail] = Field(default_factory=list)
    follow_up_required: bool

    @field_validator("title", "summary")
    @classmethod
    def _non_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("must be a non-empty string")
        return v


# Wire-level alias for `analyses.title` / `summary`. These are required and
# non-empty in the analysis object above; on the wire they may surface as
# null for non-completed recordings (handled at the route layer).


# Lightweight reference used by RecordingDetail.
AnalysisRef = ConversationAnalysis
