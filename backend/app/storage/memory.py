"""In-memory deck store. Good enough for v0/demo. Swap for Redis when persistence matters."""
_STORE: dict[str, dict] = {}


def save_deck(deck_id: str, deck: dict) -> None:
    _STORE[deck_id] = deck


def get_deck(deck_id: str) -> dict | None:
    return _STORE.get(deck_id)


def list_deck_ids() -> list[str]:
    return list(_STORE.keys())
