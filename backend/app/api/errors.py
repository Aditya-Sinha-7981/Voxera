"""Error envelopes (§9 / §10)."""
from __future__ import annotations

from typing import Optional

from fastapi import HTTPException

from app.models.recording import RecordingError


def api_error(
    status_code: int,
    code: str,
    message: str,
) -> HTTPException:
    """Build the standard §10 error envelope as a FastAPI exception."""
    return HTTPException(status_code=status_code, detail={"error": {"code": code, "message": message}})


def recording_error(code: str, message: str) -> RecordingError:
    return RecordingError(code=code, message=message)
