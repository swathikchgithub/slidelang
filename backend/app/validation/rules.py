"""Semantic validation rules.

These run AFTER pydantic parsing. Each rule returns a list of structured errors
(empty list = pass). Errors are designed to be fed back to Claude verbatim.
"""
from dataclasses import dataclass

from app.schema.deck import Deck, Layout, Slide


@dataclass
class ValidationError:
    slide_id: str
    code: str
    message: str

    def to_dict(self) -> dict:
        return {"slide_id": self.slide_id, "code": self.code, "message": self.message}


def validate_semantic(deck: Deck) -> list[ValidationError]:
    errors: list[ValidationError] = []
    for slide in deck.slides:
        errors.extend(_check_layout_block_match(slide))
        errors.extend(_check_block_density(slide))
        errors.extend(_check_title_layout_consistency(slide))
        errors.extend(_check_overflow_risk(slide)) 
    errors.extend(_check_deck_arc(deck))
    return errors


def _check_layout_block_match(slide: Slide) -> list[ValidationError]:
    out: list[ValidationError] = []
    n = len(slide.blocks)
    if slide.layout == Layout.two_column and n < 2:
        out.append(ValidationError(
            slide.id, "TWO_COL_NEEDS_TWO_BLOCKS",
            f"Slide '{slide.id}' uses two_column layout but has {n} block(s). "
            f"Either add a second block or change layout to title_content.",
        ))
    if slide.layout == Layout.full_bleed and n != 1:
        out.append(ValidationError(
            slide.id, "FULL_BLEED_ONE_BLOCK",
            f"Slide '{slide.id}' uses full_bleed but has {n} blocks. "
            f"full_bleed renders a single block; use title_content for multiple.",
        ))
    if slide.layout == Layout.quote and n == 0:
        out.append(ValidationError(
            slide.id, "QUOTE_NEEDS_TEXT",
            f"Slide '{slide.id}' uses quote layout but has no text block.",
        ))
    return out


def _check_block_density(slide: Slide) -> list[ValidationError]:
    out: list[ValidationError] = []
    chart_count = sum(1 for b in slide.blocks if b.kind == "chart")
    if chart_count > 1:
        out.append(ValidationError(
            slide.id, "TOO_MANY_CHARTS",
            f"Slide '{slide.id}' has {chart_count} charts. "
            f"Use one chart per slide; split into separate slides.",
        ))
    if chart_count == 1 and len(slide.blocks) > 2:
        out.append(ValidationError(
            slide.id, "CHART_CROWDED",
            f"Slide '{slide.id}' has a chart plus {len(slide.blocks) - 1} other blocks. "
            f"A chart slide should have at most one supporting text block.",
        ))
    return out


def _check_title_layout_consistency(slide: Slide) -> list[ValidationError]:
    out: list[ValidationError] = []
    if slide.layout == Layout.title and not slide.title:
        out.append(ValidationError(
            slide.id, "TITLE_LAYOUT_NEEDS_TITLE",
            f"Slide '{slide.id}' uses title layout but has no title field set.",
        ))
    return out


def _check_deck_arc(deck: Deck) -> list[ValidationError]:
    if deck.slides[0].layout != Layout.title:
        return [ValidationError(
            deck.slides[0].id, "FIRST_SLIDE_SHOULD_BE_TITLE",
            f"First slide '{deck.slides[0].id}' is not a title slide. "
            f"Consider setting layout=title for the opener.",
        )]
    return []

# --- Slide height estimation -----------------------------------------------
# Reveal.js renders into a fixed 960x700 canvas at default zoom. After the
# slide title (~120px) and top/bottom padding (~40px each), we have roughly
# 500-550px of usable vertical space for block content.
#
# These heights are deliberate over-estimates. We'd rather flag a slide that
# *might* overflow than miss one that *does* overflow.

# Per-block-type height estimates in CSS pixels at default zoom
_BLOCK_HEIGHT_OVERHEAD = 30   # vertical margin between blocks
_TEXT_LINE_HEIGHT = 55        # body text line height (~1.6em at 24px)
_TEXT_CHARS_PER_LINE = 35     # rough wrap point for body text in a content slide
_BULLET_LINE_HEIGHT = 55      # bullets are slightly larger than body text
_MATH_DISPLAY_HEIGHT = 140    # display math (inline-style block)
_CODE_LINE_HEIGHT = 28        # monospace line height
_CHART_HEIGHT = 380           # chart canvas
_IMAGE_HEIGHT = 320           # image figure (caption included)
_USABLE_HEIGHT = 540          # canvas minus title and padding



def _estimate_block_height(block) -> int:
    """Conservatively estimate a block's rendered height in CSS pixels."""
    kind = block.kind
    if kind == "text":
        lines = max(1, len(block.content) // _TEXT_CHARS_PER_LINE + 1)
        return _BLOCK_HEIGHT_OVERHEAD + lines * _TEXT_LINE_HEIGHT
    if kind == "bullets":
        return _BLOCK_HEIGHT_OVERHEAD + len(block.items) * _BULLET_LINE_HEIGHT
    if kind == "math":
        # Display math is the dominant case; inline math is rare here.
        return _BLOCK_HEIGHT_OVERHEAD + _MATH_DISPLAY_HEIGHT
    if kind == "code":
        # Count newlines; minimum 3 lines for the box itself.
        line_count = max(3, block.content.count("\n") + 1)
        return _BLOCK_HEIGHT_OVERHEAD + line_count * _CODE_LINE_HEIGHT
    if kind == "chart":
        return _BLOCK_HEIGHT_OVERHEAD + _CHART_HEIGHT
    if kind == "image":
        return _BLOCK_HEIGHT_OVERHEAD + _IMAGE_HEIGHT
    return _BLOCK_HEIGHT_OVERHEAD  # unknown block, be safe


def _check_overflow_risk(slide: Slide) -> list[ValidationError]:
    """Flag slides whose estimated content height exceeds the canvas.

    Two-column layouts get a pass — content is split across two columns, so
    vertical pressure is halved.
    Title-only slides get a pass — they have no body content.
    Quote and full_bleed layouts also get a pass — they use a single dominant
    block that the compiler scales to fit.
    """
    if slide.layout in (Layout.title, Layout.quote, Layout.full_bleed):
        return []
    if slide.layout == Layout.two_column:
        # Estimate the taller of the two halves
        n = len(slide.blocks)
        if n < 2:
            return []  # covered by TWO_COL_NEEDS_TWO_BLOCKS
        left_height = sum(_estimate_block_height(b) for b in slide.blocks[: n // 2 + n % 2])
        right_height = sum(_estimate_block_height(b) for b in slide.blocks[n // 2 + n % 2 :])
        worst = max(left_height, right_height)
        if worst <= _USABLE_HEIGHT:
            return []
        return [ValidationError(
            slide.id, "SLIDE_OVERFLOW_RISK",
            f"Slide '{slide.id}' (two_column) has a column estimated at "
            f"{worst}px which exceeds the ~{_USABLE_HEIGHT}px canvas height. "
            f"Shorten the text, split into two slides, or drop a block.",
        )]

    # title_content (or anything else) — sum all block heights
    total = sum(_estimate_block_height(b) for b in slide.blocks)
    if total <= _USABLE_HEIGHT:
        return []
    return [ValidationError(
        slide.id, "SLIDE_OVERFLOW_RISK",
        f"Slide '{slide.id}' has block content estimated at {total}px which "
        f"exceeds the ~{_USABLE_HEIGHT}px canvas height. Likely cause: a long "
        f"text block stacked above a math, chart, code, or image block. "
        f"Shorten the text to ~300 chars or split into two slides.",
    )]