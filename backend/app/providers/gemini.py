"""Gemini Flash analyzer (§15 + §17 + §17.1 retry contract).

Two-pass implementation:
  1. First call: structured-output / JSON-mode against the ConversationAnalysis schema.
     If the response fails Pydantic validation, retry exactly once with the
     specific validation error(s) appended to the prompt (§17.1 — corrective, not
     identical). If the retry also fails, raise `GeminiValidationFailure` and
     let the processing service mark the recording `failed` with ANALYSIS_FAILED.

Prompt content encodes §14 (bilingual, code-switched, informal) and §17
(no fabrication, schema-only output, etc.).
"""
from __future__ import annotations

import json
import logging
from typing import Any

from pydantic import ValidationError

from app.models.analysis import ConversationAnalysis
from app.models.transcript import Transcript

logger = logging.getLogger("voxera.providers.gemini")

SYSTEM_INSTRUCTION = """You analyze transcripts of hotel/hostel guest conversations.

Strict rules:
- The transcript may contain STT errors, informal speech, and noise.
- Hindi and English may be mixed (code-switching).
- Do NOT translate the transcript.
- Do NOT invent facts that are not present in the conversation.
- Do NOT invent missing booking details (booking reference, room number, dates, times).
- Do NOT invent speaker identities or roles.
- If a field has no supporting evidence, use an empty array, false, null, or "unknown"
  as appropriate. Never fabricate.
- Return ONLY a single JSON object matching the schema. No markdown fences, no commentary.

Title guidance:
- A short, history-sidebar-style label (2-4 words). Examples: "AC complaint",
  "Booking inquiry", "Wi-Fi issue". Avoid generic phrases like "Conversation".

Conversation type:
- One of: booking, complaint, inquiry, cancellation, check_in, check_out,
  maintenance, request, general, other. Use "other" if unsure.

Sentiment:
- label: positive | neutral | negative.
- score: float in [0.0, 1.0]; a confidence/strength indicator, not a precise
  psychological measurement.

Action items:
- Each must include action text, optional department, priority
  (low | medium | high), and status (requested | promised | completed | unknown).
"""


class GeminiError(Exception):
    """Raised on transport or unexpected Gemini failures."""


class GeminiValidationFailure(Exception):
    """Raised when Gemini returns output that fails Pydantic validation after
    the §17.1 corrective retry. Processing service maps this to ANALYSIS_FAILED.
    """

    def __init__(self, first_error: str, second_error: str) -> None:
        super().__init__("gemini_validation_failed_after_retry")
        self.first_error = first_error
        self.second_error = second_error


def _analysis_schema_hint() -> dict[str, Any]:
    """A JSON-Schema-ish hint for Gemini's structured output.

    Generated from the Pydantic model so the schema stays in lock-step.
    Gemini's Developer API rejects `additionalProperties` (Enterprise-only),
    so we strip it recursively before sending.
    """
    schema = ConversationAnalysis.model_json_schema()
    # Strip metadata that confuses some Gemini schema validators.
    schema.pop("title", None)
    schema.pop("$schema", None)
    _strip_additional_properties(schema)
    return schema


def _strip_additional_properties(node: Any) -> None:
    """Remove `additionalProperties` from a nested JSON-schema dict (mutating).

    Gemini's Developer API schema validator rejects `additionalProperties` at any
    level with `additionalProperties is only supported in Gemini Enterprise
    Agent Platform mode`. Pydantic emits it on every model by default.
    """
    if isinstance(node, dict):
        node.pop("additionalProperties", None)
        for value in node.values():
            _strip_additional_properties(value)
    elif isinstance(node, list):
        for item in node:
            _strip_additional_properties(item)


def _render_retry_hint(error: str) -> str:
    return (
        "Your previous response failed validation because: "
        f"{error}. "
        "Return only a single valid JSON object matching the schema, with no "
        "markdown fences or commentary. If a field has no supporting evidence, "
        "use null, an empty array, or 'unknown' as appropriate — do not invent."
    )


class GeminiAnalyzer:
    """Real Gemini Flash integration.

    Use `google-genai`'s structured-output (response_schema) where supported,
    and validate with Pydantic on our side. On Pydantic failure, retry once
    with the validation error appended to the corrective user turn.
    """

    name = "gemini"

    def __init__(self, api_key: str = "", model: str = "gemini-2.5-flash") -> None:
        if not api_key:
            raise GeminiError("GEMINI_API_KEY is required for the real Gemini analyzer.")
        from google import genai

        self._client = genai.Client(api_key=api_key)
        self._model = model

    def analyze(self, transcript: Transcript) -> ConversationAnalysis:
        user_prompt = self._build_user_prompt(transcript)
        first = self._call_once(user_prompt)
        try:
            return ConversationAnalysis.model_validate(first)
        except ValidationError as ve:
            logger.warning("gemini_first_attempt_invalid errors=%s", ve.json())
            retry_prompt = user_prompt + "\n\n" + _render_retry_hint(ve.json())
            second = self._call_once(retry_prompt)
            try:
                return ConversationAnalysis.model_validate(second)
            except ValidationError as ve2:
                logger.error("gemini_retry_invalid errors=%s", ve2.json())
                raise GeminiValidationFailure(
                    first_error=ve.json(),
                    second_error=ve2.json(),
                ) from ve2

    # ---- internals -----------------------------------------------------

    def _build_user_prompt(self, transcript: Transcript) -> str:
        return (
            "Analyze the following hotel conversation transcript and return a JSON "
            "object matching the schema.\n\n"
            "Language hint: "
            f"{transcript.language or 'auto-detect (likely en, hi, or hi-en)'}.\n\n"
            "Transcript:\n"
            "```\n"
            f"{transcript.text}\n"
            "```"
        )

    def _call_once(self, user_prompt: str) -> dict[str, Any]:
        """Single Gemini call. Returns the parsed JSON dict (not yet Pydantic-validated)."""
        from google import genai
        from google.genai import types

        schema = _analysis_schema_hint()
        config = types.GenerateContentConfig(
            system_instruction=SYSTEM_INSTRUCTION,
            response_mime_type="application/json",
            response_schema=schema,
            temperature=0.2,
        )
        try:
            response = self._client.models.generate_content(
                model=self._model,
                contents=user_prompt,
                config=config,
            )
        except Exception as exc:  # noqa: BLE001
            raise GeminiError(f"gemini_call_failed: {exc}") from exc

        # The SDK gives us .text (already JSON because of response_mime_type).
        text = (response.text or "").strip()
        if not text:
            raise GeminiError("gemini_returned_empty_text")
        try:
            return json.loads(text)
        except json.JSONDecodeError as exc:
            raise GeminiError(f"gemini_returned_non_json: {exc}: {text[:200]}") from exc
