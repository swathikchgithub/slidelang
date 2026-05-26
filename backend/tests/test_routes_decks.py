"""GET /api/decks/{id} and PATCH /api/decks/{id} route tests."""
import pytest

from app.storage.memory import save_deck


# ---------------------------------------------------------------------------
# GET /api/decks/{deck_id}
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_deck_found(client, minimal_deck):
    await save_deck("d001", minimal_deck)
    res = await client.get("/api/decks/d001")
    assert res.status_code == 200
    data = res.json()
    assert data["deck_id"] == "d001"
    assert data["deck"]["meta"]["title"] == "Test Deck"


@pytest.mark.asyncio
async def test_get_deck_not_found_returns_404(client):
    res = await client.get("/api/decks/missing")
    assert res.status_code == 404


# ---------------------------------------------------------------------------
# PATCH /api/decks/{deck_id}
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_patch_deck_valid_update(client, minimal_deck):
    await save_deck("d002", minimal_deck)
    updated = dict(minimal_deck)
    updated["meta"] = dict(minimal_deck["meta"])
    updated["meta"]["title"] = "Updated Title"

    res = await client.patch("/api/decks/d002", json=updated)
    assert res.status_code == 200
    data = res.json()
    assert data["deck"]["meta"]["title"] == "Updated Title"


@pytest.mark.asyncio
async def test_patch_deck_invalid_schema_returns_400(client):
    res = await client.patch("/api/decks/x", json={"garbage": True})
    assert res.status_code == 400


@pytest.mark.asyncio
async def test_patch_deck_error_is_structured(client):
    """400 body must have 'message' and 'errors' keys — not a raw pydantic string."""
    res = await client.patch("/api/decks/x", json={"version": "1.0"})
    assert res.status_code == 400
    detail = res.json()["detail"]
    assert "message" in detail
    assert "errors" in detail
    assert isinstance(detail["errors"], list)


@pytest.mark.asyncio
async def test_patch_deck_persists_to_storage(client, minimal_deck):
    """After a PATCH the new data is immediately readable via GET."""
    await save_deck("d003", minimal_deck)
    updated = dict(minimal_deck)
    updated["meta"] = {**minimal_deck["meta"], "title": "Persisted"}

    await client.patch("/api/decks/d003", json=updated)

    get_res = await client.get("/api/decks/d003")
    assert get_res.json()["deck"]["meta"]["title"] == "Persisted"
