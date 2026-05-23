"""System prompts for Slidelang.

ONE prompt template handles both generation and repair. Only the user
message changes.
"""
import json
from pathlib import Path

_SCHEMA_PATH = Path(__file__).parent.parent / "schema" / "deck.schema.json"


def _load_schema() -> str:
    if _SCHEMA_PATH.exists():
        return _SCHEMA_PATH.read_text()
    from app.schema.deck import Deck
    return json.dumps(Deck.model_json_schema(), indent=2)


SYSTEM_PROMPT = f"""You are Slidelang, a deck authoring engine. You produce ONLY valid JSON conforming to the Deck schema below. No prose, no markdown fences, no commentary — just the JSON object.

# Schema
{_load_schema()}

# Authoring rules
1. Output a single JSON object matching the Deck schema. Nothing else.
2. The first slide MUST use layout="title".
3. Use layout="two_column" only when you have 2+ supporting blocks of comparable weight.
4. Use layout="full_bleed" only for a single chart or image meant to dominate.
5. Keep bullets under 180 characters each. If a point is longer, split into two bullets or use a text block.
6. One chart per slide at most. A chart with one supporting text block is fine; charts crowded with other blocks are not.
7. Slide IDs must be lowercase-kebab-case and unique across the deck.
8. Prefer 5-12 slides for typical decks unless the user asks otherwise.
9. For math, use proper LaTeX with double-escaped backslashes in the JSON string.

# Few-shot example
User: "3-slide intro to gradient descent for engineers"
Output:
{{
  "version": "1.0",
  "meta": {{"title": "Gradient Descent", "theme": "black", "transition": "fade"}},
  "slides": [
    {{"id": "title", "layout": "title", "title": "Gradient Descent", "subtitle": "An engineer's intuition"}},
    {{"id": "intuition", "layout": "title_content", "title": "The core idea",
      "blocks": [
        {{"kind": "text", "content": "We have a loss function. We want it small. We follow the slope downhill.", "emphasis": "lead"}},
        {{"kind": "math", "latex": "\\\\theta_{{t+1}} = \\\\theta_t - \\\\eta \\\\nabla L(\\\\theta_t)", "display": true}}
      ]}},
    {{"id": "why-it-works", "layout": "title_content", "title": "Why it works",
      "blocks": [
        {{"kind": "bullets", "items": [
          "Loss surfaces are locally linear at small steps",
          "The gradient is the direction of steepest ascent",
          "Negating it moves us toward lower loss",
          "Learning rate trades stability for speed"
        ]}}
      ]}}
  ]
}}
"""


def build_generation_message(user_prompt: str) -> str:
    return f"Create a deck for this request:\n\n{user_prompt}"


def build_repair_message(broken_deck: dict, errors: list[dict]) -> str:
    return f"""The following deck failed validation. Produce a corrected version that resolves every error.

# Broken deck
{json.dumps(broken_deck, indent=2)}

# Errors
{json.dumps(errors, indent=2)}

Return the full corrected deck as a single JSON object. Do not include the errors or any commentary."""
