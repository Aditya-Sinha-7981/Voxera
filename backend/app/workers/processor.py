"""In-process worker (§7.1 + §7.3).

The simplest workable option for "a few recordings per day": an asyncio task
bounded by a semaphore. No external queue. The future DB-backed poller (deferred
per §7.1) replaces the trigger mechanism, not this module's contract.
"""
from __future__ import annotations

import asyncio
import logging
from functools import lru_cache

from app.config import get_settings
from app.services.processing import run_processing

logger = logging.getLogger("voxera.worker")


@lru_cache(maxsize=1)
def _semaphore() -> asyncio.Semaphore:
    return asyncio.Semaphore(get_settings().max_concurrent_jobs)


def schedule(recording_id: str) -> None:
    """Schedule a processing task under the concurrency cap.

    Returns immediately. The actual work happens in the background.
    """
    loop = asyncio.get_running_loop()
    loop.create_task(_guarded_run(recording_id))


async def _guarded_run(recording_id: str) -> None:
    sem = _semaphore()
    async with sem:
        try:
            await run_processing(recording_id)
        except Exception as exc:  # noqa: BLE001
            # `run_processing` already handles internal failures and marks
            # the recording `failed`. This is a true last-resort guard.
            logger.exception("worker_unhandled recording_id=%s error=%s", recording_id, exc)
