from collections.abc import Iterator
from functools import cache
from typing import Any

from app.services.claim_seed import load_seed_claims, seed_id

from .golden import golden_json, golden_text

__all__ = [
    "DOCUMENT",
    "PIECE",
    "STREAM",
    "TERM",
    "citations_in",
    "golden_json",
    "seed_citations",
    "seed_claims",
    "seed_source_id",
    "seed_sources",
    "sentences_in",
    "stream_events",
]

DOCUMENT = "explainer.document.golden.json"
PIECE = "explainer.piece.golden.json"
TERM = "explainer.term.golden.json"
STREAM = "explainer.stream.golden.sse"


@cache
def seed_rows() -> dict[str, Any]:
    return load_seed_claims()


@cache
def seed_claims() -> dict[str, dict[str, Any]]:
    return {str(seed_id("claim", row["id"])): row for row in seed_rows()["claims"]}


@cache
def seed_sources() -> dict[str, dict[str, Any]]:
    return {str(seed_id("source", row["id"])): row for row in seed_rows()["sources"]}


@cache
def seed_citations() -> dict[str, dict[str, Any]]:
    found = {}
    for row in seed_rows()["claims"]:
        for index, cite in enumerate(row.get("sources") or []):
            found[str(seed_id("claim-source", f"{row['id']}:{index}"))] = {
                "claimId": str(seed_id("claim", row["id"])),
                "sourceId": str(seed_id("source", cite["sourceId"])),
                "quote": cite.get("quote"),
                "locator": cite.get("locator"),
                "level": row["evidenceLevel"],
            }
    return found


def seed_source_id(key: str) -> str:
    return str(seed_id("source", key))


def citations_in(value: Any) -> Iterator[dict[str, Any]]:
    if isinstance(value, dict):
        if {"claimId", "sourceId", "evidence"} <= value.keys():
            yield value
        for item in value.values():
            yield from citations_in(item)
    elif isinstance(value, list):
        for item in value:
            yield from citations_in(item)


def sentences_in(value: Any) -> Iterator[dict[str, Any]]:
    if isinstance(value, dict):
        if {"text", "level", "citations"} <= value.keys():
            yield value
        for item in value.values():
            yield from sentences_in(item)
    elif isinstance(value, list):
        for item in value:
            yield from sentences_in(item)


def stream_events() -> list[tuple[str | None, Any]]:
    events: list[tuple[str | None, Any]] = []
    for block in golden_text(STREAM).split("\n\n"):
        if not block:
            continue
        if block.startswith(":"):
            events.append((None, block))
            continue
        name, data = block.split("\n")
        events.append((name.removeprefix("event: "), data.removeprefix("data: ")))
    return events
