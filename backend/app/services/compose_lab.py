from __future__ import annotations

import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from app.research.page_proposals import PageComponent

from .compose_held import About, Composition, CraftHeld, HeldMaterial, composed, refused
from .compose_parts import FIGURE, UnitBook, composed_component, joined, key_word, rich_formula

__all__ = ["EXPERIMENTS_MAX", "OPTION_FACTS_MAX", "experiment_lab"]

EXPERIMENTS_MIN = 2
EXPERIMENTS_MAX = 3
OPTION_FACTS_MAX = 2
LAB_FIGURE = "chem:1"
PICKER = "Choose an experiment"
TOO_FEW = (
    "two choices {name}'s own facts compare: propose_structure ALTERNATIVE for {slug}, naming a material and "
    "the material that stands in for it with the fact that says so, for a second material; {slug} holds {count}"
)
NO_MATERIAL = (
    "the material {key}: {slug} holds no material of its own with a stated alternative under that key"
)


@dataclass(frozen=True)
class _Choice:
    material: HeldMaterial
    options: tuple[tuple[HeldMaterial, tuple[uuid.UUID, ...]], ...]


def experiment_lab(craft: CraftHeld, about: About) -> Composition:
    choices = _choices(craft)
    if about.material is not None:
        chosen = [choice for choice in choices if choice.material.key == about.material]
        if not chosen:
            return refused(NO_MATERIAL.format(key=about.material, slug=craft.slug))
        choices = [*chosen, *(choice for choice in choices if choice not in chosen)]
    if len(choices) < EXPERIMENTS_MIN:
        return refused(TOO_FEW.format(name=craft.name, slug=craft.slug, count=len(choices)))
    toggles = [_toggle(craft, choice) for choice in choices[:EXPERIMENTS_MAX]]
    return composed(*toggles, _lab(craft, choices[:EXPERIMENTS_MAX], toggles))


def _choices(craft: CraftHeld) -> list[_Choice]:
    found: list[_Choice] = []
    for material in craft.materials:
        own = craft.stated(material.claim_ids)
        options = [(material, own)] if own else []
        for key, claim in material.alternatives:
            other = craft.material(key)
            stated = craft.stated([claim, *(other.claim_ids if other is not None else ())])
            if other is not None and claim in stated:
                options.append((other, stated))
        if len(options) >= EXPERIMENTS_MIN and options[0][0] is material:
            found.append(_Choice(material, tuple(options)))
    return found


def _toggle(craft: CraftHeld, choice: _Choice) -> PageComponent:
    book = UnitBook()
    experiment = key_word(choice.material.key)
    names = [option.name for option, _ in choice.options]
    question = f"{joined(names, 'or')}?"
    every = tuple(claim for _, claims in choice.options for claim in claims)
    spec = {
        "experiment": experiment,
        "questionId": f"{experiment}-q",
        "question": book.label(question, every),
        "options": [_option(craft, option, claims, book) for option, claims in choice.options],
        "textParts": [],
        "visualParts": _formulas(choice.options),
    }
    title = f"{joined(names, 'or')}, for {craft.name}"
    piece = {
        "name": f"what-if-{experiment}",
        "kind": "choice_toggle",
        "title": title,
        "description": (
            f"One choice {craft.name}'s own facts compare: {joined(names, 'or')}, each option with the facts "
            f"that state it. It sits in the what-if lab of {craft.name}, which draws it."
        ),
        "spec": spec,
    }
    return composed_component(craft, piece, book)


def _option(
    craft: CraftHeld, material: HeldMaterial, claims: Sequence[uuid.UUID], book: UnitBook
) -> dict[str, Any]:
    parts = [
        {"part": "text", "unit": book.cited(craft.facts[c].text, [c])} for c in claims[:OPTION_FACTS_MAX]
    ]
    return {
        "value": key_word(material.key),
        "label": material.name,
        "heading": book.label(material.name, claims),
        "parts": parts,
    }


def _formulas(options: Sequence[tuple[HeldMaterial, tuple[uuid.UUID, ...]]]) -> list[dict[str, Any]]:
    parts: list[dict[str, Any]] = []
    for material, _ in options:
        compound = material.compound
        formula = rich_formula(compound.formula) if compound is not None else None
        if compound is None or formula is None:
            continue
        chip = {"formula": formula, "name": compound.name, "cid": compound.cid, "source": None}
        parts.append({"part": "formulas", "option": key_word(material.key), "chips": [chip]})
    return parts


def _lab(craft: CraftHeld, choices: Sequence[_Choice], toggles: Sequence[PageComponent]) -> PageComponent:
    book = UnitBook()
    experiments = [
        {
            "key": key_word(choice.material.key),
            "label": choice.material.name,
            "toggle": {"component": toggle.proposal.label},
        }
        for choice, toggle in zip(choices, toggles, strict=True)
    ]
    spec = {
        "id": f"lab-{craft.label_root()}",
        "figure": LAB_FIGURE,
        "number": book.label(FIGURE),
        "pickerLabel": PICKER,
        "experiments": experiments,
    }
    piece = {
        "name": "what-if-lab",
        "kind": "experiment_lab",
        "title": f"What if, for {craft.name}",
        "description": (
            f"The what-if lab of {craft.name}: pick an experiment, then choose between the materials its own facts "
            f"compare, each choice with the facts that state it. Place it in the chemistry chapter of its page."
        ),
        "spec": spec,
    }
    return composed_component(craft, piece, book)
