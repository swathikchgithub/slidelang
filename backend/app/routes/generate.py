"""POST /api/generate — prompt → validated deck."""
import json
import logging
import uuid

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.ai.generator import generate_deck, repair_deck
from app.storage.memory import save_deck
from app.validation.pipeline import validate_with_repair

log = logging.getLogger(__name__)

router = APIRouter()


class GenerateRequest(BaseModel):
    prompt: str
    # Note: max_repair_attempts was previously declared but never used.
    # The pipeline uses its internal MAX_REPAIR_ATTEMPTS=2 constant.
    # Plumbing it through is a v1 task; for now, the field is removed to
    # avoid promising what we don't deliver.


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
    if len(req.prompt) > 1000:
        raise HTTPException(
            400,
            "prompt is too long (max 1000 chars). Try a shorter description.",
        )

    # --- Initial generation ----------------------------------------------
    try:
        raw = await generate_deck(req.prompt)
    except json.JSONDecodeError:
        # Claude returned malformed JSON — usually truncation from
        # max_tokens on very large prompts.
        log.exception("Claude returned non-JSON")
        raise HTTPException(
            502,
            detail={
                "message": (
                    "The AI returned malformed output. This often happens with "
                    "very large or complex prompts. Try a smaller deck "
                    "(5-15 slides) or simpler requirements."
                ),
                "error_type": "non_json_response",
            },
        )
    except Exception as e:
        log.exception("Unexpected error during initial generation")
        raise HTTPException(
            502,
            detail={
                "message": "Unexpected error during generation. Please try again.",
                "error_type": type(e).__name__,
            },
        )

    # --- Validate + repair loop ------------------------------------------
    async def _repair(broken: dict, errors: list[dict]) -> dict:
        """
        Wrap repair_deck with defensive error handling. A failed repair
        should NOT crash the request — we return the original broken deck
        and let validation surface the remaining errors as warnings.
        """
        try:
            return await repair_deck(broken, errors)
        except json.JSONDecodeError:
            log.warning("Repair returned non-JSON; aborting repair")
            return broken
        except Exception:
            log.exception("Repair call failed; aborting repair")
            return broken

    result = await validate_with_repair(raw, repair_fn=_repair)

    if result.deck is None:
        raise HTTPException(
            422,
            detail={
                "message": "Could not produce a valid deck after repair attempts",
                "errors": [e.to_dict() for e in result.errors],
            },
        )

    # --- Persist and respond ---------------------------------------------
    deck_dict = result.deck.model_dump(mode="json")
    deck_id = str(uuid.uuid4())[:8]
    save_deck(deck_id, deck_dict)

    return GenerateResponse(
        deck_id=deck_id,
        deck=deck_dict,
        repaired=result.repaired,
        attempts=result.attempts,
        warnings=[e.to_dict() for e in result.errors],
    )