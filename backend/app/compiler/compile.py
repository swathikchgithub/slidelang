"""Spec → reveal.js HTML compiler. Pure function. Deterministic."""
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.compiler.primitives import render_block, render_layout
from app.schema.deck import Deck, Slide

_TEMPLATE_DIR = Path(__file__).parent / "templates"
_env = Environment(
    loader=FileSystemLoader(_TEMPLATE_DIR),
    autoescape=select_autoescape(["html", "j2", "html.j2"]),
    trim_blocks=True,
    lstrip_blocks=True,
)


def compile_deck(deck: Deck) -> str:
    """Compile a validated Deck into a standalone reveal.js HTML document."""
    slides_html = [_compile_slide(s) for s in deck.slides]
    return _env.get_template("deck.html.j2").render(
        meta=deck.meta,
        slides_html=slides_html,
    )


def _compile_slide(slide: Slide) -> str:
    blocks_html = [render_block(b) for b in slide.blocks]
    body = render_layout(slide.layout, slide.title, slide.subtitle, blocks_html)
    notes = (
        f'<aside class="notes">{_escape(slide.notes)}</aside>'
        if slide.notes else ""
    )
    return f'<section id="{slide.id}">{body}{notes}</section>'


def _escape(s: str) -> str:
    return (
        s.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )
