"""Storage layer tests — in-memory mode (no Redis)."""
import pytest

from app.storage.memory import MAX_STORE_SIZE, _STORE, get_deck, save_deck


@pytest.mark.asyncio
async def test_save_and_get_deck():
    deck = {"version": "1.0", "meta": {"title": "T"}, "slides": []}
    await save_deck("abc", deck)
    result = await get_deck("abc")
    assert result == deck


@pytest.mark.asyncio
async def test_get_missing_deck_returns_none():
    result = await get_deck("nonexistent")
    assert result is None


@pytest.mark.asyncio
async def test_overwrite_existing_deck():
    original = {"meta": {"title": "Original"}}
    updated = {"meta": {"title": "Updated"}}
    await save_deck("x", original)
    await save_deck("x", updated)
    result = await get_deck("x")
    assert result["meta"]["title"] == "Updated"


@pytest.mark.asyncio
async def test_cap_evicts_oldest_entry():
    """When the store is full, the oldest entry is removed to make room."""
    # Fill the store to exactly the cap
    for i in range(MAX_STORE_SIZE):
        await save_deck(f"deck-{i}", {"index": i})

    assert len(_STORE) == MAX_STORE_SIZE
    # deck-0 is the oldest — it must still be there before we exceed the cap
    assert await get_deck("deck-0") is not None

    # Adding one more should evict deck-0
    await save_deck("deck-overflow", {"index": MAX_STORE_SIZE})

    assert len(_STORE) == MAX_STORE_SIZE
    assert await get_deck("deck-0") is None
    assert await get_deck("deck-overflow") is not None


@pytest.mark.asyncio
async def test_cap_does_not_evict_below_limit():
    """Saving fewer than MAX_STORE_SIZE decks never evicts anything."""
    for i in range(10):
        await save_deck(f"keep-{i}", {"index": i})

    for i in range(10):
        assert await get_deck(f"keep-{i}") is not None


@pytest.mark.asyncio
async def test_multiple_decks_are_independent():
    await save_deck("a", {"data": 1})
    await save_deck("b", {"data": 2})
    assert (await get_deck("a"))["data"] == 1
    assert (await get_deck("b"))["data"] == 2
