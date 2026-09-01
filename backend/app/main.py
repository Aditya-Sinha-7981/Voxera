"""FastAPI app factory.

Lifespan hooks:
  * Startup: §7.4 reconcile stale recordings + §10.3 sweep orphan temp dirs.
  * Shutdown: dispose the STT model so Whisper's memory is released.
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import health, recordings
from app.config import get_settings
from app.providers import get_stt_provider
from app.services.reconciliation import reconcile_stale_recordings, sweep_orphan_temp_dirs

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
# Propagate uvicorn's access logger through our logging configuration so the
# access log lines are visible alongside the application logs.
logging.getLogger("uvicorn.access").handlers = logging.getLogger().handlers
logging.getLogger("uvicorn.access").propagate = True


@asynccontextmanager
async def lifespan(app: FastAPI):
    await reconcile_stale_recordings()
    sweep_orphan_temp_dirs()
    try:
        yield
    finally:
        provider = get_stt_provider()
        shutdown = getattr(provider, "shutdown", None)
        if callable(shutdown):
            shutdown()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="Voxera", version="0.1.0", lifespan=lifespan)

    origins = [o.strip() for o in settings.frontend_url.split(",") if o.strip()]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins or ["*"],
        allow_credentials=False,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["*"],
    )

    app.include_router(recordings.router)
    app.include_router(health.router)
    return app


app = create_app()
