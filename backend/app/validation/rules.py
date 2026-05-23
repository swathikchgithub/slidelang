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
