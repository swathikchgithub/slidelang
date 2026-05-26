"""Shared fixtures for all test modules."""
import json
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
import app.routes.generate as _generate_mod
import app.storage.memory as _storage_mod

FIXTURES = Path(__file__).parent / "fixtures"


# ---------------------------------------------------------------------------
# HTTP test client
# ---------------------------------------------------------------------------

@pytest.fixture
async def client():
    """Async HTTPX client wired directly to the FastAPI app (no real TCP)."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        yield c


# ---------------------------------------------------------------------------
# State isolation — reset module-level stores between every test
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def clear_storage():
    """Wipe the in-memory deck store before and after each test."""
    _storage_mod._STORE.clear()
    yield
    _storage_mod._STORE.clear()


@pytest.fixture(autouse=True)
def clear_rate_buckets():
    """Reset the rate-limiter sliding-window state before and after each test."""
    _generate_mod._rate_buckets.clear()
    yield
    _generate_mod._rate_buckets.clear()


# ---------------------------------------------------------------------------
# Deck fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def minimal_deck() -> dict:
    return {
        "version": "1.0",
        "meta": {"title": "Test Deck"},
        "slides": [{"id": "title", "layout": "title", "title": "Hello"}],
    }


@pytest.fixture
def good_deck() -> dict:
    return json.loads((FIXTURES / "good_deck.json").read_text())
