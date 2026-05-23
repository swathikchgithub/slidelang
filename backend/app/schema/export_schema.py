"""Emit the JSON Schema for the Deck DSL — for prompting and docs.

Run with: python -m app.schema.export_schema
"""
import json
from pathlib import Path

from app.schema.deck import Deck


def get_deck_schema() -> dict:
    return Deck.model_json_schema()


def write_schema_file(path: Path) -> None:
    path.write_text(json.dumps(get_deck_schema(), indent=2))


if __name__ == "__main__":
    out = Path(__file__).parent / "deck.schema.json"
    write_schema_file(out)
    print(f"Wrote {out}")
