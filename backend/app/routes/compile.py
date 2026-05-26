"""POST /api/compile — deck spec → HTML.
GET  /api/compile/{id} — stored deck → HTML.
"""
from fastapi import APIRouter, HTTPException, Response

from app.compiler.compile import compile_deck
from app.schema.deck import Deck
from app.storage.memory import get_deck
from app.validation.rules import validate_semantic

router = APIRouter()


@router.post("/compile", response_class=Response)
async def compile_post(deck_dict: dict):
    try:
        deck = Deck.model_validate(deck_dict)
    except Exception as e:
        raise HTTPException(400, detail={"message": f"Schema validation failed: {e}"})

    semantic_errors = validate_semantic(deck)
    if semantic_errors:
        raise HTTPException(
            422,
            detail={
                "message": "Deck failed semantic validation",
                "errors": [e.to_dict() for e in semantic_errors],
            },
        )

    return Response(content=compile_deck(deck), media_type="text/html")


@router.get("/compile/{deck_id}", response_class=Response)
async def compile_get(deck_id: str):
    raw = await get_deck(deck_id)
    if raw is None:
        raise HTTPException(404, "deck not found")
    deck = Deck.model_validate(raw)
    return Response(content=compile_deck(deck), media_type="text/html")
