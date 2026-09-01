"""Transcript model — the normalized internal representation (§12).

Used both as the response shape in API §7 and as the output type of every
SpeechToTextProvider.
"""
from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel


class Segment(BaseModel):
    """A single transcript segment (API §7)."""

    model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel)

    speaker: Optional[str] = None
    role: Optional[str] = None  # e.g. "guest" / "hotel_staff" — never fabricated.
    start: Optional[float] = None  # seconds
    end: Optional[float] = None  # seconds
    text: str


class Transcript(BaseModel):
    """Normalized transcript (§12)."""

    model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel)

    language: Optional[str] = None
    text: str = Field(default="")
    segments: List[Segment] = Field(default_factory=list)


# Lightweight reference used by RecordingDetail. Mirrors the API §7 shape.
TranscriptRef = Transcript
