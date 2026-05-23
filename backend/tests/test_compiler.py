"""Compiler tests: determinism, escaping, output shape."""
import json
from pathlib import Path

from app.compiler.compile import compile_deck
from app.schema.deck import Deck

FIXTURES = Path(__file__).parent / "fixtures"


def _load_good() -> Deck:
    raw = json.loads((FIXTURES / "good_deck.json").read_text())
    return Deck.model_validate(raw)


def test_compile_is_deterministic():
    deck = _load_good()
    assert compile_deck(deck) == compile_deck(deck)


def test_compile_contains_all_slides():
    deck = _load_good()
    html = compile_deck(deck)
    for slide in deck.slides:
        assert f'id="{slide.id}"' in html


def test_compile_escapes_user_content_in_blocks():
    """XSS attempt in text content must be escaped."""
    deck = Deck.model_validate({
        "version": "1.0",
        "meta": {"title": "XSS"},
        "slides": [{
            "id": "s1",
            "blocks": [{"kind": "text", "content": "<script>alert('x')</script>"}],
        }],
    })
    html = compile_deck(deck)
    assert "<script>alert" not in html
    assert "&lt;script&gt;" in html


def test_compile_escapes_meta_title():
    """The meta.title goes through Jinja autoescape (j2 extension)."""
    deck = Deck.model_validate({
        "version": "1.0",
        "meta": {"title": "<script>alert(1)</script>"},
        "slides": [{"id": "s1", "layout": "title", "title": "T"}],
    })
    html = compile_deck(deck)
    assert "<script>alert(1)</script>" not in html
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in html


def test_compile_includes_reveal_assets():
    html = compile_deck(_load_good())
    assert "reveal.js@5" in html
    assert "katex" in html
    assert "chart.js@4" in html


def test_chart_payload_is_escaped_json():
    deck = Deck.model_validate({
        "version": "1.0",
        "meta": {"title": "Chart"},
        "slides": [
            {"id": "title", "layout": "title", "title": "T"},
            {"id": "c", "blocks": [{
                "kind": "chart", "chart_type": "bar",
                "labels": ["a", "b"], "series": [{"name": "s", "values": [1, 2]}],
            }]},
        ],
    })
    html = compile_deck(deck)
    assert 'data-chart-config="' in html
    assert "&quot;type&quot;" in html


def test_all_layouts_render():
    layouts = ["title", "title_content", "two_column", "full_bleed", "quote"]
    for layout in layouts:
        deck = Deck.model_validate({
            "version": "1.0",
            "meta": {"title": f"L-{layout}"},
            "slides": [{
                "id": "s1",
                "layout": layout,
                "title": "T",
                "blocks": (
                    [{"kind": "text", "content": "a"}, {"kind": "text", "content": "b"}]
                    if layout == "two_column"
                    else [{"kind": "text", "content": "x"}]
                ),
            }],
        })
        html = compile_deck(deck)
        assert "<section" in html
