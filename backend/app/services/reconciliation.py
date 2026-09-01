"""Startup reconciliation (§7.4) and orphan temp-file sweep (§10.3).

Both runs are best-effort and idempotent. They are the second line of defense
behind the per-recording try/finally cleanup.
"""
from __future__ import annotations

import logging
import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path

from app.config import get_settings
from app.services import storage

logger = logging.getLogger("voxera.reconciliation")


async def reconcile_stale_recordings() -> int:
    """Mark recordings stuck in non-terminal states past the grace period as `failed` (§7.4).

    Returns the number of recordings marked.
    """
    grace = get_settings().reconciliation_grace_period_seconds
    try:
        ids = storage.find_stale_non_terminal(grace)
    except storage.StorageError as exc:
        logger.error("reconciliation_lookup_failed error=%s", exc)
        return 0
    for rid in ids:
        try:
            storage.mark_interrupted(rid)
            logger.warning("reconciled_interrupted recording_id=%s", rid)
        except storage.StorageError as exc:
            logger.error("reconciliation_mark_failed recording_id=%s error=%s", rid, exc)
    return len(ids)


def sweep_orphan_temp_dirs() -> int:
    """Remove per-recording temp dirs older than the grace period (§10.3)."""
    base = Path(get_settings().temp_audio_dir)
    if not base.exists():
        return 0
    grace = get_settings().reconciliation_grace_period_seconds
    cutoff = datetime.now(timezone.utc) - timedelta(seconds=grace)
    removed = 0
    for child in base.iterdir():
        if not child.is_dir():
            continue
        try:
            mtime = datetime.fromtimestamp(child.stat().st_mtime, tz=timezone.utc)
        except FileNotFoundError:
            continue
        if mtime < cutoff:
            try:
                shutil.rmtree(child, ignore_errors=True)
                removed += 1
                logger.warning("orphan_temp_removed path=%s", child)
            except Exception as exc:  # noqa: BLE001
                logger.error("orphan_temp_remove_failed path=%s error=%s", child, exc)
    return removed
