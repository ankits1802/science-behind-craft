from __future__ import annotations

import re
import uuid
from collections.abc import Collection, Sequence
from typing import Any

from app.core.errors import InvalidInput
from app.research.component_specs_general_delivery import CLAIMS_PER_UNIT_MAX, LABEL_MAX_CHARS, DeliveredUnit
from app.research.page_proposals import PageComponent
from app.research.quotes import unsupported_figures
from app.research.unit_ids import UNIT_PREFIX

from .compose_held import CraftHeld, HeldMaterial

__all__ = [
    "COMPOSED_FIELD",
    "FIGURE",
    "UnitBook",
    "composed_component",
    "joined",
    "key_word",
    "material_named",
    "rich_formula",
    "species_token",
    "unique_word",
]

COMPOSED_FIELD = "CHEMISTRY"
FIGURE = "Figure"
CRAFT_SUBJECT = "CRAFT"
UNIT_DIGITS = 4
KEY_WORD_MAX = 40
NOT_KEY = re.compile(r"[^a-z0-9]+")
RUN = re.compile(r"\d+|\D+")
CHARGE = re.compile(r"\^?(\d*[+-])$")
SUBSCRIPTED_AFTER = frozenset(")]")
UNSTATED = (
    "the text {text!r} holds a number or a formula or runs past {most} characters, and no fact of the page "
    "states it, so it cannot stand as a label"
)

RichRun = str | dict[str, str]


class UnitBook:
    def __init__(self) -> None:
        self._units: dict[str, DeliveredUnit] = {}

    def cited(self, text: str, claim_ids: Sequence[uuid.UUID]) -> str:
        return self._added(
            DeliveredUnit(text=text, claim_ids=list(dict.fromkeys(claim_ids))[:CLAIMS_PER_UNIT_MAX])
        )

    def label(self, text: str, claim_ids: Sequence[uuid.UUID] = ()) -> str:
        if len(text) <= LABEL_MAX_CHARS and not unsupported_figures(text, ()):
            return self._added(DeliveredUnit(text=text))
        if not claim_ids:
            raise InvalidInput(UNSTATED.format(text=text, most=LABEL_MAX_CHARS))
        return self.cited(text, claim_ids)

    def units(self) -> dict[str, DeliveredUnit]:
        return dict(self._units)

    def _added(self, unit: DeliveredUnit) -> str:
        ref = f"{UNIT_PREFIX}{len(self._units) + 1:0{UNIT_DIGITS}d}"
        self._units[ref] = unit
        return ref


def composed_component(craft: CraftHeld, piece: dict[str, Any], book: UnitBook) -> PageComponent:
    proposal = {
        "label": f"{craft.label_root()}/{COMPOSED_FIELD.lower()}/{piece['name']}",
        "title": piece["title"],
        "description": piece["description"],
        "kind": piece["kind"],
        "field": COMPOSED_FIELD,
        "craft_slug": craft.slug,
        "subjects": [{"kind": CRAFT_SUBJECT, "key": craft.slug}],
        "spec": piece["spec"],
        "units": book.units(),
    }
    return PageComponent.model_validate({"proposal": proposal, "cites": {}})


def joined(names: Sequence[str], word: str = "and") -> str:
    if len(names) <= 1:
        return "".join(names)
    return f"{', '.join(names[:-1])} {word} {names[-1]}"


def key_word(text: str) -> str:
    word = NOT_KEY.sub("-", text.casefold()).strip("-")[:KEY_WORD_MAX].strip("-") or "part"
    return word if word[0].isalpha() else f"part-{word}"[:KEY_WORD_MAX].strip("-")


def unique_word(text: str, taken: Collection[str]) -> str:
    base = key_word(text)
    found, n = base, 1
    while found in taken:
        n += 1
        found = f"{base[: KEY_WORD_MAX - 3]}-{n}"
    return found


def material_named(craft: CraftHeld, name: str) -> HeldMaterial | None:
    wanted = name.casefold().strip()
    for material in craft.materials:
        names = {material.name.casefold()}
        if material.compound is not None:
            names.add(material.compound.name.casefold())
        if wanted in names:
            return material
    return None


def species_token(craft: CraftHeld, name: str) -> str | None:
    material = material_named(craft, name)
    return material.tokens[0] if material is not None and material.tokens else None


def rich_formula(formula: str | None) -> list[RichRun] | None:
    text = (formula or "").strip()
    if not text:
        return None
    charge = CHARGE.search(text) if text[-1] in "+-" else None
    body = text[: charge.start()] if charge else text
    runs: list[RichRun] = []
    for found in RUN.finditer(body):
        piece = found.group(0)
        before = body[found.start() - 1] if found.start() else ""
        if piece.isdigit() and (before.isalpha() or before in SUBSCRIPTED_AFTER):
            runs.append({"text": piece, "style": "sub"})
        elif runs and isinstance(last := runs[-1], str):
            runs[-1] = last + piece
        else:
            runs.append(piece)
    if charge:
        runs.append({"text": charge.group(1), "style": "sup"})
    return runs or None
