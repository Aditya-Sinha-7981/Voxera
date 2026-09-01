"""Custom Pydantic JSON serialization for API §1.2 compliance.

Pydantic's default emits `+00:00` for UTC datetimes; the API contract
requires `Z`. We serialize datetimes here and let the route layer /
JSON encoder route through this.
"""
from __future__ import annotations

from datetime import datetime, timezone


def to_iso_z(value: datetime) -> str:
    """Render a datetime as ISO 8601 UTC with `Z` suffix (API §1.2)."""
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    else:
        value = value.astimezone(timezone.utc)
    return value.strftime("%Y-%m-%dT%H:%M:%SZ")
