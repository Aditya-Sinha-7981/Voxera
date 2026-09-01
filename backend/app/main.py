"""Phase 2 stub main.py — no provider shutdown on lifespan."""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import health, recordings
from app.config import get_settings
from app.services.reconciliation import reconcile_stale_recordings, sweep_orphan_temp_dirs

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await reconcile_stale_recordings()
    sweep_orphan_temp_dirs()
    yield


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
