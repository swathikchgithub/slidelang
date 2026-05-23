"""Per-block and per-layout renderers. Pure functions returning HTML strings.

Every user-controlled string passes through html.escape. No exceptions.
"""
import html
import json

from app.schema.deck import (
    Block,
    BulletsBlock,
    ChartBlock,
    CodeBlock,
    ImageBlock,
    Layout,
    MathBlock,
    TextBlock,
)


def render_block(block: Block) -> str:
    if isinstance(block, TextBlock):
        return _text(block)
    if isinstance(block, BulletsBlock):
        return _bullets(block)
    if isinstance(block, ImageBlock):
        return _image(block)
    if isinstance(block, MathBlock):
        return _math(block)
    if isinstance(block, CodeBlock):
        return _code(block)
    if isinstance(block, ChartBlock):
        return _chart(block)
    raise ValueError(f"unknown block: {type(block).__name__}")


def _text(b: TextBlock) -> str:
    cls = {"normal": "sl-text", "lead": "sl-lead", "caption": "sl-caption"}[b.emphasis]
    return f'<p class="{cls}">{html.escape(b.content)}</p>'


def _bullets(b: BulletsBlock) -> str:
    items = "".join(f"<li>{html.escape(i)}</li>" for i in b.items)
    return f'<ul class="sl-bullets">{items}</ul>'


def _image(b: ImageBlock) -> str:
    cap = f'<figcaption>{html.escape(b.caption)}</figcaption>' if b.caption else ""
    return (
        f'<figure class="sl-image">'
        f'<img src="{html.escape(b.src)}" alt="{html.escape(b.alt)}">'
        f'{cap}</figure>'
    )


def _math(b: MathBlock) -> str:
    open_d, close_d = ("$$", "$$") if b.display else ("\\(", "\\)")
    return f'<div class="sl-math">{open_d}{b.latex}{close_d}</div>'


def _code(b: CodeBlock) -> str:
    return (
        f'<pre class="sl-code"><code class="language-{html.escape(b.language)}">'
        f'{html.escape(b.content)}</code></pre>'
    )


def _chart(b: ChartBlock) -> str:
    config = {
        "type": b.chart_type,
        "data": {
            "labels": b.labels,
            "datasets": [{"label": s.name, "data": s.values} for s in b.series],
        },
        "options": {
            "responsive": True,
            "maintainAspectRatio": False,
            "plugins": {"title": {"display": bool(b.title), "text": b.title or ""}},
        },
    }
    payload = html.escape(json.dumps(config))
    return (
        f'<div class="sl-chart">'
        f'<canvas data-chart-config="{payload}"></canvas>'
        f'</div>'
    )


def render_layout(layout: Layout, title, subtitle, blocks_html: list[str]) -> str:
    if layout == Layout.title:
        return _layout_title(title, subtitle)
    if layout == Layout.title_content:
        return _layout_title_content(title, blocks_html)
    if layout == Layout.two_column:
        return _layout_two_column(title, blocks_html)
    if layout == Layout.full_bleed:
        return _layout_full_bleed(blocks_html)
    if layout == Layout.quote:
        return _layout_quote(title, blocks_html)
    raise ValueError(f"unknown layout: {layout}")


def _layout_title(title, subtitle) -> str:
    t = f'<h1>{html.escape(title or "")}</h1>'
    s = f'<p class="sl-subtitle">{html.escape(subtitle or "")}</p>' if subtitle else ""
    return f'<div class="sl-layout-title">{t}{s}</div>'


def _layout_title_content(title, blocks_html) -> str:
    t = f'<h2>{html.escape(title or "")}</h2>' if title else ""
    body = "".join(blocks_html)
    return f'<div class="sl-layout-tc">{t}<div class="sl-body">{body}</div></div>'


def _layout_two_column(title, blocks_html) -> str:
    t = f'<h2>{html.escape(title or "")}</h2>' if title else ""
    half = (len(blocks_html) + 1) // 2
    left = "".join(blocks_html[:half])
    right = "".join(blocks_html[half:])
    return (
        f'<div class="sl-layout-2col">{t}'
        f'<div class="sl-col">{left}</div>'
        f'<div class="sl-col">{right}</div>'
        f'</div>'
    )


def _layout_full_bleed(blocks_html) -> str:
    return f'<div class="sl-layout-bleed">{"".join(blocks_html)}</div>'


def _layout_quote(title, blocks_html) -> str:
    attribution = f'<footer>— {html.escape(title)}</footer>' if title else ""
    return (
        f'<blockquote class="sl-quote">'
        f'{"".join(blocks_html)}{attribution}'
        f'</blockquote>'
    )
