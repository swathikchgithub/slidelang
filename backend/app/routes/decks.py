"""GET /api/decks/{id} and PATCH /api/decks/{id}."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ValidationError as PydanticError

from app.schema.deck import Deck
from app.storage.memory import get_deck, save_deck

router = APIRouter()


class DeckResponse(BaseModel):
    deck_id: str
    deck: dict


@router.get("/decks/{deck_id}", response_model=DeckResponse)
async def read_deck(deck_id: str):
    raw = await get_deck(deck_id)
    if raw is None:
        raise HTTPException(404, "deck not found")
    return DeckResponse(deck_id=deck_id, deck=raw)


@router.patch("/decks/{deck_id}", response_model=DeckResponse)
async def update_deck(deck_id: str, deck_dict: dict):
    """Re-validate on every save. The DSL is the contract."""
    try:
        deck = Deck.model_validate(deck_dict)
    except PydanticError as e:
        raise HTTPException(
            400,
            detail={
                "message": "Deck schema validation failed",
                "errors": e.errors(include_url=False),
            },
        )
    await save_deck(deck_id, deck.model_dump(mode="json"))
    return DeckResponse(deck_id=deck_id, deck=deck.model_dump(mode="json"))
