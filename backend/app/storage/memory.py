"""Deck store — in-memory by default, Redis-backed if REDIS_URL is set.

In-memory mode caps at MAX_STORE_SIZE entries; oldest entry is evicted when the
cap is hit. Redis mode persists across restarts with a 24-hour TTL per deck.

Both modes expose the same async interface so callers are implementation-agnostic.
"""
import json
import logging
from collections import OrderedDict

log = logging.getLogger(__name__)

MAX_STORE_SIZE = 500
_DECK_TTL_SECONDS = 60 * 60 * 24  # 24 hours

# In-memory store: insertion-ordered so we can evict the oldest entry.
_STORE: OrderedDict[str, dict] = OrderedDict()

# Redis client — populated at startup if REDIS_URL is configured.
_redis = None


def _init_redis() -> None:
    global _redis
    try:
        from app.config import settings
        if not settings.REDIS_URL:
            return
        import redis.asyncio as aioredis  # type: ignore[import]
        _redis = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
        log.info("Storage: Redis backend at %s", settings.REDIS_URL)
    except ImportError:
        log.warning("redis package not installed; using in-memory store")
    except Exception as exc:  # pragma: no cover
        log.warning("Redis init failed (%s); using in-memory store", exc)


_init_redis()


async def save_deck(deck_id: str, deck: dict) -> None:
    if _redis is not None:
        await _redis.setex(f"deck:{deck_id}", _DECK_TTL_SECONDS, json.dumps(deck))
        return
    if len(_STORE) >= MAX_STORE_SIZE:
        _STORE.popitem(last=False)  # evict oldest
    _STORE[deck_id] = deck
    _STORE.move_to_end(deck_id)


async def get_deck(deck_id: str) -> dict | None:
    if _redis is not None:
        raw = await _redis.get(f"deck:{deck_id}")
        return json.loads(raw) if raw else None
    return _STORE.get(deck_id)
