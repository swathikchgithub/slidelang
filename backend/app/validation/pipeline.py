"""The validate → repair → revalidate loop.

This is the heart of the AI quality story. Pydantic + semantic rules produce
a structured error list; we feed it back to Claude with the broken deck and
ask for a corrected version. Bounded retries.
"""
import logging
from dataclasses import dataclass
from typing import Awaitable, Callable

from pydantic import ValidationError as PydanticError

from app.schema.deck import Deck
from app.validation.rules import ValidationError, validate_semantic

log = logging.getLogger(__name__)

MAX_REPAIR_ATTEMPTS = 2

RepairFn = Callable[[dict, list[dict]], Awaitable[dict]]


@dataclass
class ValidationResult:
    deck: Deck | None
    errors: list[ValidationError]
    attempts: int
    repaired: bool


def parse_and_validate(raw: dict) -> tuple[Deck | None, list[ValidationError]]:
    """One pass: pydantic (structural) + semantic rules."""
    try:
        deck = Deck.model_validate(raw)
    except PydanticError as e:
        errs = [
            ValidationError(
                slide_id=_extract_slide_id(err["loc"]),
                code="SCHEMA_" + str(err["type"]).upper(),
                message=f"At {'.'.join(str(x) for x in err['loc'])}: {err['msg']}",
            )
            for err in e.errors()
        ]
        return None, errs

    semantic_errs = validate_semantic(deck)
    return deck, semantic_errs


def _extract_slide_id(loc: tuple) -> str:
    if len(loc) >= 2 and loc[0] == "slides":
        return f"slide#{loc[1]}"
    return "deck"


async def validate_with_repair(raw: dict, repair_fn: RepairFn) -> ValidationResult:
    """Run validation; on errors, call repair_fn; revalidate. Bounded retries."""
    attempt = 0
    current_raw = raw
    repaired = False

    while attempt <= MAX_REPAIR_ATTEMPTS:
        deck, errors = parse_and_validate(current_raw)
        if deck is not None and not errors:
            return ValidationResult(
                deck=deck, errors=[], attempts=attempt, repaired=repaired,
            )

        if attempt == MAX_REPAIR_ATTEMPTS:
            log.warning(
                "Repair exhausted at attempt %d with %d errors", attempt, len(errors)
            )
            return ValidationResult(
                deck=deck, errors=errors, attempts=attempt, repaired=repaired,
            )

        log.info("Attempt %d had %d errors; requesting repair", attempt, len(errors))
        err_dicts = [e.to_dict() for e in errors]
        current_raw = await repair_fn(current_raw, err_dicts)
        repaired = True
        attempt += 1

    return ValidationResult(deck=None, errors=[], attempts=attempt, repaired=repaired)
