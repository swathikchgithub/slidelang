"""GET /api/decks/{id} and PATCH /api/decks/{id}."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.schema.deck import Deck
from app.storage.memory import get_deck, save_deck

router = APIRouter()


class DeckResponse(BaseModel):
    deck_id: str
    deck: dict


@router.get("/decks/{deck_id}", response_model=DeckResponse)
async def read_deck(deck_id: str):
    raw = get_deck(deck_id)
    if raw is None:
        raise HTTPException(404, "deck not found")
    return DeckResponse(deck_id=deck_id, deck=raw)


@router.patch("/decks/{deck_id}", response_model=DeckResponse)
async def update_deck(deck_id: str, deck_dict: dict):
    """Re-validate on every save. The DSL is the contract."""
    try:
        deck = Deck.model_validate(deck_dict)
    except Exception as e:
        raise HTTPException(400, f"invalid deck: {e}")
    save_deck(deck_id, deck.model_dump(mode="json"))
    return DeckResponse(deck_id=deck_id, deck=deck.model_dump(mode="json"))
