"""Schema tests: round-tripping and validators."""
import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.schema.deck import (
    BulletsBlock,
    ChartBlock,
    ChartSeries,
    Deck,
    MathBlock,
    Slide,
    TextBlock,
)


FIXTURES = Path(__file__).parent / "fixtures"


def test_good_deck_parses():
    raw = json.loads((FIXTURES / "good_deck.json").read_text())
    deck = Deck.model_validate(raw)
    assert deck.meta.title == "Slidelang Demo Deck"
    assert len(deck.slides) == 6


def test_minimal_deck():
    deck = Deck.model_validate({
        "version": "1.0",
        "meta": {"title": "Tiny"},
        "slides": [{"id": "only"}],
    })
    assert deck.slides[0].layout.value == "title_content"
    assert deck.meta.theme.value == "black"


def test_bullet_too_long_fails():
    with pytest.raises(ValidationError) as exc:
        BulletsBlock(items=["x" * 200])
    assert "exceeds 180 chars" in str(exc.value)


def test_chart_series_length_must_match_labels():
    with pytest.raises(ValidationError) as exc:
        ChartBlock(
            chart_type="bar",
            labels=["a", "b", "c"],
            series=[ChartSeries(name="x", values=[1, 2])],
        )
    assert "values" in str(exc.value)


def test_duplicate_slide_ids_fail():
    with pytest.raises(ValidationError):
        Deck.model_validate({
            "version": "1.0",
            "meta": {"title": "Dup"},
            "slides": [{"id": "a"}, {"id": "a"}],
        })


def test_slide_id_pattern():
    with pytest.raises(ValidationError):
        Slide(id="Has Spaces")
    with pytest.raises(ValidationError):
        Slide(id="UPPERCASE")


def test_mathblock_accepts_valid_latex():
    block = MathBlock(latex=r"\theta_{t+1} = \theta_t - \eta \nabla L(\theta_t)")
    assert block.display is True


def test_mathblock_rejects_html_angle_brackets():
    with pytest.raises(ValidationError) as exc:
        MathBlock(latex=r"\text{<script>alert(1)</script>}")
    assert "latex must not contain" in str(exc.value)


def test_mathblock_rejects_gt_sign():
    with pytest.raises(ValidationError):
        MathBlock(latex=r"a > b")


def test_discriminator_dispatches_correctly():
    deck = Deck.model_validate({
        "version": "1.0",
        "meta": {"title": "Mixed"},
        "slides": [{
            "id": "s1",
            "blocks": [
                {"kind": "text", "content": "hi"},
                {"kind": "bullets", "items": ["one", "two"]},
            ],
        }],
    })
    blocks = deck.slides[0].blocks
    assert isinstance(blocks[0], TextBlock)
    assert isinstance(blocks[1], BulletsBlock)
