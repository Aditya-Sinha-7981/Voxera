"""Conftest — fixtures shared across the test suite.

These tests target the synchronous surface area (URL validation, response
shape). End-to-end tests that exercise Supabase or Whisper are written in
Phase 3 alongside the real providers, with fixtures that mock the storage
layer.
"""
from __future__ import annotations

import pytest


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"
