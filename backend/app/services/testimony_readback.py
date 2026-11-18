from __future__ import annotations

import uuid
from collections.abc import Iterator, Mapping
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.research.explainer import Explainer

from .testimony_store import TestimonyQuote, quote_states

__all__ = ["ITEM_PREFIX", "current_quotes", "kalavigyan_ids", "refreshed_document"]

ITEM_PREFIX = "kalavigyan:"
ARTISAN_VOICE = "artisan_voice"
TESTIMONY_ORIGIN = "KALAVIGYAN"


def _blocks(document: Mapping[str, Any]) -> Iterator[dict[str, Any]]:
    for section in document.get("sections") or []:
        for block in section.get("blocks") or []:
            if block.get("kind") == ARTISAN_VOICE:
                yield block


def _contribution_id(quote: Mapping[str, Any]) -> uuid.UUID | None:
    item = str(quote.get("itemId") or "")
    if quote.get("origin") != TESTIMONY_ORIGIN or not item.startswith(ITEM_PREFIX):
        return None
    try:
        return uuid.UUID(item.removeprefix(ITEM_PREFIX))
    except ValueError:
        return None


def kalavigyan_ids(document: Mapping[str, Any]) -> list[uuid.UUID]:
    found = (_contribution_id(quote) for block in _blocks(document) for quote in block.get("quotes") or [])
    return [contribution_id for contribution_id in found if contribution_id is not None]


def _speaker(state: TestimonyQuote) -> dict[str, Any]:
    credit = state.speaker
    return {
        "name": credit.name,
        "role": credit.role,
        "district": credit.district or None,
        "state": credit.state or None,
        "line": credit.line,
    }


def _cited_ids(document: Mapping[str, Any]) -> set[str]:
    cited: set[str] = set()
    for section in document.get("sections") or []:
        for block in section.get("blocks") or []:
            cited |= _ids_in(block)
    if document.get("lede"):
        cited |= _ids_in(document["lede"])
    return cited


def _ids_in(value: Any) -> set[str]:
    if isinstance(value, Mapping):
        found = {str(value[key]) for key in ("sourceId",) if value.get(key)}
        for child in value.values():
            found |= _ids_in(child)
        return found
    if isinstance(value, list):
        return {item for child in value for item in _ids_in(child)}
    return set()


def refreshed_document(
    document: dict[str, Any], states: Mapping[uuid.UUID, TestimonyQuote]
) -> dict[str, Any]:
    sources: dict[str, Mapping[str, Any]] = {}
    for block in _blocks(document):
        kept: list[dict[str, Any]] = []
        for quote in block.get("quotes") or []:
            contribution_id = _contribution_id(quote)
            if contribution_id is None:
                kept.append(quote)
            elif contribution_id in states:
                state = states[contribution_id]
                kept.append({**quote, "speaker": _speaker(state)})
                sources[str(state.source_id)] = state.source
            else:
                block["removed"] = int(block.get("removed") or 0) + 1
        block["quotes"] = kept
    cited = _cited_ids(document)
    document["sources"] = [
        dict(sources.get(str(source["id"]), source))
        for source in document.get("sources") or []
        if source["id"] in cited
    ]
    return document


async def current_quotes(session: AsyncSession, explainer: Explainer) -> Explainer:
    document = explainer.model_dump(mode="json", by_alias=True)
    wanted = kalavigyan_ids(document)
    if not wanted:
        return explainer
    states = await quote_states(session, wanted)
    return Explainer.model_validate(refreshed_document(document, states))
