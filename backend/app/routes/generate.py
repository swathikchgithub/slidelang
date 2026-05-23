"""POST /api/generate — prompt → validated deck."""
import uuid

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.ai.generator import generate_deck, repair_deck
from app.storage.memory import save_deck
from app.validation.pipeline import validate_with_repair

router = APIRouter()


class GenerateRequest(BaseModel):
    prompt: str
    max_repair_attempts: int = 2


class GenerateResponse(BaseModel):
    deck_id: str
    deck: dict
    repaired: bool
    attempts: int
    warnings: list[dict]


@router.post("/generate", response_model=GenerateResponse)
async def generate(req: GenerateRequest):
    if not req.prompt.strip():
        raise HTTPException(400, "prompt cannot be empty")

    raw = await generate_deck(req.prompt)

    async def _repair(broken: dict, errors: list[dict]) -> dict:
        return await repair_deck(broken, errors)

    result = await validate_with_repair(raw, repair_fn=_repair)

    if result.deck is None:
        raise HTTPException(
            422,
            detail={
                "message": "Could not produce a valid deck after repair attempts",
                "errors": [e.to_dict() for e in result.errors],
            },
        )

    deck_id = str(uuid.uuid4())[:8]
    save_deck(deck_id, result.deck.model_dump(mode="json"))

    return GenerateResponse(
        deck_id=deck_id,
        deck=result.deck.model_dump(mode="json"),
        repaired=result.repaired,
        attempts=result.attempts,
        warnings=[e.to_dict() for e in result.errors],
    )
