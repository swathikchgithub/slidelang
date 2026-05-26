"""POST /api/generate route tests. Claude is always mocked — no real API calls."""
import json

import pytest

import app.routes.generate as generate_mod

# A minimal valid deck dict that a mocked Claude would return.
_VALID_DECK = {
    "version": "1.0",
    "meta": {"title": "Mocked Deck"},
    "slides": [{"id": "title", "layout": "title", "title": "Hello"}],
}


@pytest.fixture
def mock_generate(monkeypatch):
    """Patch generate_deck to return _VALID_DECK without touching Anthropic."""
    async def _fake(prompt: str) -> dict:
        return _VALID_DECK

    monkeypatch.setattr(generate_mod, "generate_deck", _fake)


# ---------------------------------------------------------------------------
# Input validation (no Claude needed)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_generate_empty_prompt_returns_400(client):
    res = await client.post("/api/generate", json={"prompt": "   "})
    assert res.status_code == 400


@pytest.mark.asyncio
async def test_generate_prompt_too_long_returns_400(client):
    res = await client.post("/api/generate", json={"prompt": "x" * 1001})
    assert res.status_code == 400


@pytest.mark.asyncio
async def test_generate_missing_prompt_field_returns_422(client):
    res = await client.post("/api/generate", json={})
    assert res.status_code == 422


# ---------------------------------------------------------------------------
# Rate limiting (still mocked so we don't hit Claude 10 times)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_generate_rate_limit_blocks_after_10_requests(client, mock_generate):
    for _ in range(10):
        r = await client.post("/api/generate", json={"prompt": "test deck"})
        assert r.status_code == 200

    eleventh = await client.post("/api/generate", json={"prompt": "test deck"})
    assert eleventh.status_code == 429
    detail = eleventh.json()["detail"]
    assert detail["error_type"] == "rate_limited"
    assert "message" in detail


@pytest.mark.asyncio
async def test_generate_rate_limit_allows_under_threshold(client, mock_generate):
    for _ in range(9):
        r = await client.post("/api/generate", json={"prompt": "test deck"})
        assert r.status_code == 200


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_generate_success_returns_deck_id_and_deck(client, mock_generate):
    res = await client.post("/api/generate", json={"prompt": "5 slides on Python"})
    assert res.status_code == 200
    data = res.json()
    assert "deck_id" in data
    assert len(data["deck_id"]) == 8
    assert data["deck"]["meta"]["title"] == "Mocked Deck"
    assert data["repaired"] is False
    assert data["attempts"] == 0


@pytest.mark.asyncio
async def test_generate_success_deck_is_persisted(client, mock_generate):
    """Deck must be reachable via GET after generation."""
    gen = await client.post("/api/generate", json={"prompt": "test"})
    deck_id = gen.json()["deck_id"]

    get = await client.get(f"/api/decks/{deck_id}")
    assert get.status_code == 200
    assert get.json()["deck"]["meta"]["title"] == "Mocked Deck"


# ---------------------------------------------------------------------------
# Claude error paths
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_generate_non_json_from_claude_returns_502(client, monkeypatch):
    async def _bad_generate(prompt: str) -> dict:
        raise json.JSONDecodeError("bad", "", 0)

    monkeypatch.setattr(generate_mod, "generate_deck", _bad_generate)

    res = await client.post("/api/generate", json={"prompt": "test"})
    assert res.status_code == 502
    detail = res.json()["detail"]
    assert detail["error_type"] == "non_json_response"
    assert "message" in detail


@pytest.mark.asyncio
async def test_generate_unexpected_error_returns_502(client, monkeypatch):
    async def _crash(prompt: str) -> dict:
        raise RuntimeError("unexpected boom")

    monkeypatch.setattr(generate_mod, "generate_deck", _crash)

    res = await client.post("/api/generate", json={"prompt": "test"})
    assert res.status_code == 502
    assert "message" in res.json()["detail"]


# ---------------------------------------------------------------------------
# Repair path
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_generate_triggers_repair_on_semantic_error(client, monkeypatch):
    """If Claude returns a deck with a semantic error, repair should be attempted."""
    broken = {
        "version": "1.0",
        "meta": {"title": "Broken"},
        "slides": [
            # Missing title layout on first slide → FIRST_SLIDE_SHOULD_BE_TITLE
            {"id": "bad", "layout": "title_content", "title": "Oops"},
        ],
    }

    async def _broken_generate(prompt: str) -> dict:
        return broken

    async def _fix_repair(deck: dict, errors: list) -> dict:
        return _VALID_DECK

    monkeypatch.setattr(generate_mod, "generate_deck", _broken_generate)
    monkeypatch.setattr(generate_mod, "repair_deck", _fix_repair)

    res = await client.post("/api/generate", json={"prompt": "test"})
    assert res.status_code == 200
    data = res.json()
    assert data["repaired"] is True
    assert data["attempts"] >= 1
