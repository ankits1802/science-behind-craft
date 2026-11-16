from __future__ import annotations

import uuid
from collections.abc import Mapping, Sequence
from typing import Any

from pydantic import TypeAdapter

from app.research.crafts import CraftRef
from app.schemas.voice import ClientToolCall
from app.services.knowledge_view import ClaimView

__all__ = ["MAP_CONCEPT_TYPES", "turn_actions"]

MAP_CONCEPT_TYPES = frozenset({"ENVIRONMENTAL_CONDITION"})
TOOL_CALL = TypeAdapter(ClientToolCall)


def turn_actions(
    *,
    answer_id: uuid.UUID | None,
    session_craft: CraftRef | None,
    turn_craft: CraftRef | None,
    cited: Sequence[ClaimView],
    stage_of: Mapping[uuid.UUID, uuid.UUID],
) -> tuple[dict[str, Any], ...]:
    if answer_id is None or not cited:
        return ()
    calls: list[dict[str, Any]] = [{"name": "show_sources", "parameters": {"answerId": str(answer_id)}}]
    if session_craft is not None and session_craft == turn_craft:
        calls += _craft_page_calls(session_craft, cited, stage_of)
    return tuple(_checked(call) for call in calls)


def _craft_page_calls(
    craft: CraftRef, cited: Sequence[ClaimView], stage_of: Mapping[uuid.UUID, uuid.UUID]
) -> list[dict[str, Any]]:
    calls: list[dict[str, Any]] = []
    if any(view.concept_type in MAP_CONCEPT_TYPES for view in cited):
        calls.append({"name": "show_on_map", "parameters": {"craftSlug": craft.slug}})
    stage = next((stage_of[v.concept_id] for v in cited if v.concept_id in stage_of), None)
    if stage is not None:
        calls.append({"name": "open_stage", "parameters": {"stageId": str(stage)}})
        calls.append({"name": "offer_image", "parameters": {"stageId": str(stage)}})
    return calls


def _checked(call: dict[str, Any]) -> dict[str, Any]:
    return TOOL_CALL.dump_python(TOOL_CALL.validate_python(call), mode="json", by_alias=True)
