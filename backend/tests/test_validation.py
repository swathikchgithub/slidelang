"""Validation tests: semantic rules and the repair loop."""
import json
from pathlib import Path

import pytest

from app.schema.deck import Deck
from app.validation.pipeline import parse_and_validate, validate_with_repair
from app.validation.rules import validate_semantic

FIXTURES = Path(__file__).parent / "fixtures"


def test_good_deck_has_no_semantic_errors():
    raw = json.loads((FIXTURES / "good_deck.json").read_text())
    deck = Deck.model_validate(raw)
    errors = validate_semantic(deck)
    assert errors == []


def test_broken_deck_produces_expected_codes():
    raw = json.loads((FIXTURES / "broken_deck.json").read_text())
    deck, errors = parse_and_validate(raw)
    assert deck is not None
    codes = {e.code for e in errors}
    assert "FIRST_SLIDE_SHOULD_BE_TITLE" in codes
    assert "TWO_COL_NEEDS_TWO_BLOCKS" in codes
    assert "TOO_MANY_CHARTS" in codes


def test_two_col_with_one_block_fires_rule():
    raw = {
        "version": "1.0",
        "meta": {"title": "T"},
        "slides": [
            {"id": "title", "layout": "title", "title": "T"},
            {"id": "bad", "layout": "two_column", "blocks": [
                {"kind": "text", "content": "lonely"}
            ]},
        ],
    }
    _, errors = parse_and_validate(raw)
    assert any(e.code == "TWO_COL_NEEDS_TWO_BLOCKS" for e in errors)


def test_full_bleed_with_multiple_blocks_fires_rule():
    raw = {
        "version": "1.0",
        "meta": {"title": "T"},
        "slides": [
            {"id": "title", "layout": "title", "title": "T"},
            {"id": "bad", "layout": "full_bleed", "blocks": [
                {"kind": "text", "content": "a"},
                {"kind": "text", "content": "b"},
            ]},
        ],
    }
    _, errors = parse_and_validate(raw)
    assert any(e.code == "FULL_BLEED_ONE_BLOCK" for e in errors)


@pytest.mark.asyncio
async def test_repair_loop_converges():
    broken = json.loads((FIXTURES / "broken_deck.json").read_text())

    async def fake_repair(deck, errors):
        return {
            "version": "1.0",
            "meta": {"title": "Repaired"},
            "slides": [{"id": "title", "layout": "title", "title": "T"}],
        }

    result = await validate_with_repair(broken, repair_fn=fake_repair)
    assert result.deck is not None
    assert result.repaired is True
    assert result.attempts == 1
    assert result.errors == []


@pytest.mark.asyncio
async def test_repair_loop_gives_up_after_max_attempts():
    broken = json.loads((FIXTURES / "broken_deck.json").read_text())

    async def hopeless_repair(deck, errors):
        return deck

    result = await validate_with_repair(broken, repair_fn=hopeless_repair)
    assert result.errors
    assert result.attempts == 2
