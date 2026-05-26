"""
Slidelang Deck DSL.

Design principles:
1. Closed set of block types. Claude cannot invent new ones.
2. Layout is declarative (named templates), not pixel-based. The compiler owns geometry.
3. Every optional field has a sensible default. Minimal valid deck = 3 required fields.
4. Validation errors are machine-readable; the repair loop feeds them back to Claude.
"""
from __future__ import annotations

from enum import Enum
from typing import Annotated, Literal, Union

from pydantic import BaseModel, Field, field_validator


# ---- Closed vocabularies ----------------------------------------------------

class Theme(str, Enum):
    black = "black"
    white = "white"
    league = "league"
    moon = "moon"


class Transition(str, Enum):
    none = "none"
    fade = "fade"
    slide = "slide"
    convex = "convex"


class Layout(str, Enum):
    """High-level layouts. Compiler picks CSS grid templates per value."""
    title = "title"
    title_content = "title_content"
    two_column = "two_column"
    full_bleed = "full_bleed"
    quote = "quote"


# ---- Block primitives -------------------------------------------------------

class TextBlock(BaseModel):
    kind: Literal["text"] = "text"
    content: str = Field(..., max_length=2000)
    emphasis: Literal["normal", "lead", "caption"] = "normal"


class BulletsBlock(BaseModel):
    kind: Literal["bullets"] = "bullets"
    items: list[str] = Field(..., min_length=1, max_length=8)

    @field_validator("items")
    @classmethod
    def each_bullet_bounded(cls, v: list[str]) -> list[str]:
        for i, item in enumerate(v):
            if len(item) > 180:
                raise ValueError(f"bullet[{i}] exceeds 180 chars; split into two")
        return v


class ImageBlock(BaseModel):
    kind: Literal["image"] = "image"
    src: str
    alt: str = ""
    caption: str | None = None


class MathBlock(BaseModel):
    """LaTeX rendered via KaTeX in the browser."""
    kind: Literal["math"] = "math"
    latex: str = Field(..., max_length=500)
    display: bool = True

    @field_validator("latex")
    @classmethod
    def no_html_in_latex(cls, v: str) -> str:
        if "<" in v or ">" in v:
            raise ValueError("latex must not contain '<' or '>' — use proper LaTeX commands")
        return v


class CodeBlock(BaseModel):
    kind: Literal["code"] = "code"
    language: str = "text"
    content: str = Field(..., max_length=4000)


class ChartSeries(BaseModel):
    name: str
    values: list[float]


class ChartBlock(BaseModel):
    """Charts use a tiny declarative spec, NOT raw Chart.js config."""
    kind: Literal["chart"] = "chart"
    chart_type: Literal["bar", "line", "pie"]
    title: str | None = None
    labels: list[str] = Field(..., min_length=1, max_length=20)
    series: list[ChartSeries] = Field(..., min_length=1, max_length=5)

    @field_validator("series")
    @classmethod
    def series_lengths_match_labels(cls, v, info):
        labels = info.data.get("labels", [])
        for s in v:
            if len(s.values) != len(labels):
                raise ValueError(
                    f"series '{s.name}' has {len(s.values)} values but "
                    f"there are {len(labels)} labels"
                )
        return v


Block = Annotated[
    Union[TextBlock, BulletsBlock, ImageBlock, MathBlock, CodeBlock, ChartBlock],
    Field(discriminator="kind"),
]


# ---- Slide and Deck ---------------------------------------------------------

class Slide(BaseModel):
    id: str = Field(..., pattern=r"^[a-z0-9-]{1,40}$")
    layout: Layout = Layout.title_content
    title: str | None = None
    subtitle: str | None = None
    blocks: list[Block] = Field(default_factory=list, max_length=6)
    notes: str | None = None


class DeckMeta(BaseModel):
    title: str = Field(..., max_length=200)
    author: str | None = None
    theme: Theme = Theme.black
    transition: Transition = Transition.fade


class Deck(BaseModel):
    version: Literal["1.0"] = "1.0"
    meta: DeckMeta
    slides: list[Slide] = Field(..., min_length=1, max_length=40)

    @field_validator("slides")
    @classmethod
    def unique_slide_ids(cls, v: list[Slide]) -> list[Slide]:
        ids = [s.id for s in v]
        if len(ids) != len(set(ids)):
            raise ValueError("slide ids must be unique")
        return v
