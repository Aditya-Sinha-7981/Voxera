"""Health check route (API §13)."""
from __future__ import annotations

import asyncio

from fastapi import APIRouter, Response, status

from app.services import storage

router = APIRouter(prefix="/api/v1/health", tags=["health"])


@router.get("", response_model=None)
async def health() -> Response:
    """`200 {status: ok}` only when the process is up AND the database is reachable."""
    try:
        await asyncio.to_thread(_ping_db)
        return Response(
            content='{"status":"ok"}',
            media_type="application/json",
            status_code=status.HTTP_200_OK,
        )
    except Exception:  # noqa: BLE001
        return Response(
            content='{"status":"unavailable"}',
            media_type="application/json",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        )


def _ping_db() -> None:
    """Cheap Supabase round-trip — list zero rows, capped at 1."""
    storage._client().table("recordings").select("id").limit(1).execute()
