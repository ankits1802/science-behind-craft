from __future__ import annotations

import uuid
from collections.abc import Callable, Sequence
from typing import Any

from app.research.art_kit import CLOTH_FORMS, PARTS_PER_PANEL_MAX, choice_named, parts_named_by
from app.research.colour_key import agent_materials, agent_names, first_depicted, specimen_token

from .compose_held import CraftHeld, HeldAfter, HeldStage
from .compose_parts import UnitBook

__all__ = ["PASTED_STAGES", "PRINTED", "PRINTED_STAGES", "after_token", "stage_agent_names", "stage_scene"]

PRINTED_STAGES = frozenset({"PRINT"})
PASTED_STAGES = PRINTED_STAGES | {"RESIST"}
PRINTED = "printed"
CLOTH = "cloth"
WATER = "water"

Part = dict[str, Any]
Stated = tuple[uuid.UUID, str]
Pick = Callable[[str], str | None]


def stage_scene(craft: CraftHeld, stage: HeldStage, book: UnitBook) -> dict[str, Any] | None:
    stated = _stated(craft, stage)
    parts = [
        *_piece(craft, stage, stated, book),
        *_paste(craft, stage, stated, book),
        *_said(stated, book),
    ][:PARTS_PER_PANEL_MAX]
    if not parts:
        return None
    motion = _motion(parts)
    return {"parts": parts, **({"motion": motion} if motion else {})}


def _stated(craft: CraftHeld, stage: HeldStage) -> list[Stated]:
    claims = [*stage.claim_ids]
    if stage.after is not None:
        claims.append(stage.after.claim_id)
    if stage.duration is not None:
        claims.append(stage.duration.claim_id)
    return [(claim, craft.facts[claim].text) for claim in craft.stated(claims)]


def after_token(craft: CraftHeld, stage: HeldStage, after: HeldAfter) -> str | None:
    if after.tokens:
        return after.tokens[0]
    found = first_depicted(after.colours, stage_agent_names(craft, stage))
    return specimen_token(found[1]) if found is not None else None


def stage_agent_names(craft: CraftHeld, stage: HeldStage) -> tuple[str, ...]:
    used = [found for key in stage.material_keys if (found := craft.material(key)) is not None]
    return agent_names(agent_materials(used))


def _shown(craft: CraftHeld, stage: HeldStage) -> tuple[HeldAfter, str] | None:
    after = stage.after
    if after is None or not craft.stated([after.claim_id]):
        return None
    token = after_token(craft, stage, after)
    return None if token is None else (after, token)


def _piece(craft: CraftHeld, stage: HeldStage, stated: Sequence[Stated], book: UnitBook) -> list[Part]:
    shown = _shown(craft, stage)
    vessel = _first(stated, lambda text: choice_named("bath", "vessel", text))
    if vessel is not None:
        claim, named = vessel
        bath: Part = {"part": "bath", "vessel": named}
        if shown is not None:
            bath["piece"] = shown[1]
        claims = [claim] if shown is None else [claim, shown[0].claim_id]
        return [{**bath, "label": book.cited(stage.name, claims)}]
    if shown is None:
        return []
    after, token = shown
    words = " ".join(text for _, text in stated)
    label = book.cited(craft.facts[after.claim_id].text, [after.claim_id])
    if any(part == CLOTH for part, _ in parts_named_by(words)):
        form = choice_named(CLOTH, "form", words) or CLOTH_FORMS[0]
        return [{"part": CLOTH, "form": form, "material": token, "label": label}]
    shape = choice_named("piece", "shape", words)
    return [{"part": "piece", "shape": shape, "material": token, "label": label}] if shape else []


def _paste(craft: CraftHeld, stage: HeldStage, stated: Sequence[Stated], book: UnitBook) -> list[Part]:
    if stage.stage_type not in PASTED_STAGES or not stated:
        return []
    form = choice_named("paste", "form", " ".join(text for _, text in stated))
    if form is None and stage.stage_type in PRINTED_STAGES:
        form = PRINTED
    if form is None:
        return []
    for key in stage.material_keys:
        material = craft.material(key)
        if material is not None and material.tokens:
            naming = [claim for claim, text in stated if material.name.casefold() in text.casefold()]
            label = book.cited(material.name, naming or [stated[0][0]])
            return [{"part": "paste", "form": form, "material": material.tokens[0], "label": label}]
    return []


def _said(stated: Sequence[Stated], book: UnitBook) -> list[Part]:
    parts: list[Part] = []
    heat = _first(stated, lambda text: choice_named("heat", "source", text))
    if heat is not None:
        parts.append({"part": "heat", "source": heat[1], "label": _sentence(stated, heat[0], book)})
    water = _first(stated, _water_form)
    if water is not None:
        parts.append({"part": WATER, "form": water[1], "label": _sentence(stated, water[0], book)})
    return parts


def _water_form(text: str) -> str | None:
    if not any(part == WATER for part, _ in parts_named_by(text)):
        return None
    return choice_named(WATER, "form", text)


def _first(stated: Sequence[Stated], pick: Pick) -> tuple[uuid.UUID, str] | None:
    for claim, text in stated:
        named = pick(text)
        if named is not None:
            return claim, named
    return None


def _sentence(stated: Sequence[Stated], claim: uuid.UUID, book: UnitBook) -> str:
    return book.cited(next(text for found, text in stated if found == claim), [claim])


def _motion(parts: Sequence[Part]) -> str | None:
    if any(part["part"] == "bath" and part.get("piece") for part in parts):
        return "dip"
    if any(part["part"] == CLOTH for part in parts):
        return "take"
    return None
