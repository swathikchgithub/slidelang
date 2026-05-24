"""Generate and repair decks via Claude."""
import json
import logging
import re

from app.ai.client import get_client
from app.ai.prompts import (
    SYSTEM_PROMPT,
    build_generation_message,
    build_repair_message,
)
from app.config import settings

log = logging.getLogger(__name__)

MAX_TOKENS = 8000


async def generate_deck(user_prompt: str) -> dict:
    """Initial generation. Returns raw dict (unvalidated)."""
    client = get_client()
    msg = await client.messages.create(
        model=settings.CLAUDE_MODEL,
        max_tokens=MAX_TOKENS,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": build_generation_message(user_prompt)}],
    )
    return _extract_json(msg.content[0].text)


async def repair_deck(broken: dict, errors: list) -> dict:
    """Called by the validation pipeline. Same model, different user message."""
    client = get_client()
    msg = await client.messages.create(
        model=settings.CLAUDE_MODEL,
        max_tokens=MAX_TOKENS,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": build_repair_message(broken, errors)}],
    )
    return _extract_json(msg.content[0].text)

_FENCE_OPEN_RE = re.compile(r"^```(?:json)?\s*\n?", re.IGNORECASE)
_FENCE_CLOSE_RE = re.compile(r"\n?```\s*$")


def _extract_json(text: str) -> dict:
    """Defensive: strip markdown fences (even truncated ones) before JSON parsing.

    Handles three cases:
    1. Complete fence: ```json\n{...}\n```
    2. Opening fence only (truncated mid-response): ```json\n{...
    3. No fence at all: {...}

    Raises JSONDecodeError if parsing still fails after stripping.
    """
    text = text.strip()
    # Strip opening fence if present
    text = _FENCE_OPEN_RE.sub("", text)
    # Strip closing fence if present (may be absent on truncation)
    text = _FENCE_CLOSE_RE.sub("", text)
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        log.error("Claude returned non-JSON (first 500 chars): %s", text[:500])
        raise
