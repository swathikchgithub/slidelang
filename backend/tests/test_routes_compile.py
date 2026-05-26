"""POST /api/compile and GET /api/compile/{id} route tests."""
import pytest

from app.storage.memory import save_deck


# ---------------------------------------------------------------------------
# POST /api/compile
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_compile_post_happy_path(client, minimal_deck):
    res = await client.post("/api/compile", json=minimal_deck)
    assert res.status_code == 200
    assert res.headers["content-type"].startswith("text/html")
    body = res.text
    assert "reveal.js" in body
    assert "title" in body  # slide id


@pytest.mark.asyncio
async def test_compile_post_returns_all_slide_sections(client, good_deck):
    res = await client.post("/api/compile", json=good_deck)
    assert res.status_code == 200
    for slide in good_deck["slides"]:
        assert f'id="{slide["id"]}"' in res.text


@pytest.mark.asyncio
async def test_compile_post_invalid_schema_returns_400(client):
    res = await client.post("/api/compile", json={"not": "a deck"})
    assert res.status_code == 400
    detail = res.json()["detail"]
    assert "message" in detail


@pytest.mark.asyncio
async def test_compile_post_semantic_error_returns_422(client):
    """two_column with one block violates TWO_COL_NEEDS_TWO_BLOCKS."""
    deck = {
        "version": "1.0",
        "meta": {"title": "Bad"},
        "slides": [
            {"id": "title", "layout": "title", "title": "T"},
            {"id": "bad", "layout": "two_column",
             "blocks": [{"kind": "text", "content": "lonely"}]},
        ],
    }
    res = await client.post("/api/compile", json=deck)
    assert res.status_code == 422
    detail = res.json()["detail"]
    assert detail["message"] == "Deck failed semantic validation"
    codes = [e["code"] for e in detail["errors"]]
    assert "TWO_COL_NEEDS_TWO_BLOCKS" in codes


@pytest.mark.asyncio
async def test_compile_post_full_bleed_one_block_passes_semantic(client):
    """full_bleed with exactly one block is valid."""
    deck = {
        "version": "1.0",
        "meta": {"title": "Bleed"},
        "slides": [
            {"id": "title", "layout": "title", "title": "T"},
            {"id": "bleed", "layout": "full_bleed",
             "blocks": [{"kind": "text", "content": "just me"}]},
        ],
    }
    res = await client.post("/api/compile", json=deck)
    assert res.status_code == 200


# ---------------------------------------------------------------------------
# GET /api/compile/{deck_id}
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_compile_get_stored_deck(client, minimal_deck):
    await save_deck("abc123", minimal_deck)
    res = await client.get("/api/compile/abc123")
    assert res.status_code == 200
    assert res.headers["content-type"].startswith("text/html")
    assert "reveal.js" in res.text


@pytest.mark.asyncio
async def test_compile_get_not_found_returns_404(client):
    res = await client.get("/api/compile/doesnotexist")
    assert res.status_code == 404
