"""Phase 2 stub — real impl in Phase 3.

Returns a deterministic valid analysis so the pipeline runs end-to-end
without any AI keys. Phase 3 implements the real Gemini call with §17.1
corrective retry on Pydantic failure.
"""
from __future__ import annotations

from app.models.analysis import (
    ConversationAnalysis,
    ConversationType,
    Sentiment,
    SentimentLabel,
)


class GeminiAnalyzer:
    name = "gemini"

    def __init__(self, api_key: str = "", model: str = "gemini-2.5-flash") -> None:
        self._api_key = api_key
        self._model = model

    def analyze(self, transcript) -> ConversationAnalysis:  # type: ignore[no-untyped-def]
        return ConversationAnalysis(
            title="",
            summary="",
            conversation_type=ConversationType.OTHER,
            sentiment=Sentiment(label=SentimentLabel.NEUTRAL, score=0.0),
            key_points=[],
            complaints=[],
            requests=[],
            action_items=[],
            important_details=[],
            follow_up_required=False,
        )
