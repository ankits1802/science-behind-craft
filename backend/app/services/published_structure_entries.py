from __future__ import annotations

import uuid
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any

from app.research.review_labels import cut_label
from app.research.structure_proposals import (
    BOTANICAL_NAME,
    CONFLICT,
    GLOSSARY_TERM,
    NATIVE_NAME,
    OPEN_QUESTION,
    REACTION,
    STAGE_AFTER,
    STAGE_WHY,
    parsed_item,
)

from .curated_index import CuratedPage, IndexStage
from .structure_proposals_page import OwnerPage

__all__ = ["FoundEntry", "checked_item", "edited_page", "entries_of", "page_entries", "without_entry"]


@dataclass(frozen=True)
class FoundEntry:
    kind: str
    key: str
    name: str
    claim_ids: tuple[uuid.UUID, ...]
    current: Mapping[str, Any] = field(default_factory=dict)
    fixed: Mapping[str, Any] = field(default_factory=dict)
    reaction_id: uuid.UUID | None = None
    term_key: str | None = None


def page_entries(page: OwnerPage) -> list[FoundEntry]:
    return [entry for listed in _LISTS for entry in listed(page)]


def entries_of(page: OwnerPage, claim_id: uuid.UUID, kind: str | None = None) -> list[FoundEntry]:
    return [
        entry
        for entry in page_entries(page)
        if claim_id in entry.claim_ids and (kind is None or entry.kind == kind)
    ]


def checked_item(entry: FoundEntry, fields: Mapping[str, Any]) -> Any:
    return parsed_item({"kind": entry.kind, **entry.fixed, **entry.current, **fields})


def without_entry(page: OwnerPage, entry: FoundEntry) -> OwnerPage:
    return page.model_copy(update=_WITHOUT[entry.kind](page, entry))


def edited_page(page: OwnerPage, entry: FoundEntry, fields: Mapping[str, Any]) -> OwnerPage:
    return page.model_copy(update=_EDITED[entry.kind](page, entry, dict(fields)))


def _stages(page: OwnerPage) -> list[IndexStage]:
    return page.stages if isinstance(page, CuratedPage) else []


def _afters(page: OwnerPage) -> list[FoundEntry]:
    return [
        FoundEntry(
            STAGE_AFTER,
            stage.key,
            cut_label(f"Stage {stage.key}'s colour after: {stage.after.text}"),
            (stage.after.claim_id,),
            current={"text": stage.after.text, "colours": list(stage.after.colours)},
            fixed={"stage_key": stage.key},
        )
        for stage in _stages(page)
        if stage.after is not None
    ]


def _whys(page: OwnerPage) -> list[FoundEntry]:
    return [
        FoundEntry(STAGE_WHY, stage.key, f"Stage {stage.key}'s why", (stage.why_claim_id,))
        for stage in _stages(page)
        if stage.why_claim_id is not None
    ]


def _native_names(page: OwnerPage) -> list[FoundEntry]:
    names = page.native_names if isinstance(page, CuratedPage) else []
    return [
        FoundEntry(
            NATIVE_NAME,
            name.text,
            cut_label(f"Native name: {name.text} ({name.language})"),
            (name.claim_id,),
            current={"text": name.text, "language": name.language, "script": name.script},
        )
        for name in names
    ]


def _reactions(page: OwnerPage) -> list[FoundEntry]:
    return [
        FoundEntry(
            REACTION,
            reaction.key,
            cut_label(
                f"Reaction {reaction.key}: {' + '.join(s.name for s in reaction.reactants)} to "
                f"{' + '.join(s.name for s in reaction.products)}"
            ),
            tuple(reaction.claim_ids),
            reaction_id=reaction.reaction_id,
        )
        for reaction in page.reactions
    ]


def _botanical_names(page: OwnerPage) -> list[FoundEntry]:
    return [
        FoundEntry(
            BOTANICAL_NAME,
            material.key,
            cut_label(f"Botanical name of {material.name}: {material.botanical_name}"),
            tuple(material.claim_ids),
            current={"botanical_name": material.botanical_name},
            fixed={"material_key": material.key},
        )
        for material in page.materials
        if material.botanical_name is not None
    ]


def _terms(page: OwnerPage) -> list[FoundEntry]:
    return [
        FoundEntry(
            GLOSSARY_TERM,
            term.key,
            cut_label(f"Glossary term: {term.term}"),
            tuple(term.claim_ids),
            current={"meaning": term.meaning, "language": term.language, "script": term.script},
            fixed={"term": term.term},
            term_key=term.term_key,
        )
        for term in page.glossary
    ]


def _conflicts(page: OwnerPage) -> list[FoundEntry]:
    return [
        FoundEntry(
            CONFLICT,
            conflict.about,
            cut_label(f"Conflict: {conflict.about}"),
            tuple(conflict.claim_ids),
            current={"about": conflict.about},
            fixed={"claim_ids": [str(claim) for claim in conflict.claim_ids]},
        )
        for conflict in page.conflicts
    ]


def _questions(page: OwnerPage) -> list[FoundEntry]:
    return [
        FoundEntry(
            OPEN_QUESTION,
            question.key,
            cut_label(f"Open question: {question.question}"),
            tuple(question.claim_ids),
            current={"question": question.question, "settled_by": question.settled_by},
        )
        for question in page.open_questions
    ]


def _stage_update(page: OwnerPage, key: str, update: Mapping[str, Any]) -> dict[str, Any]:
    return {"stages": [s.model_copy(update=dict(update)) if s.key == key else s for s in _stages(page)]}


def _material_update(page: OwnerPage, key: str, update: Mapping[str, Any]) -> dict[str, Any]:
    return {"materials": [m.model_copy(update=dict(update)) if m.key == key else m for m in page.materials]}


def _after_edited(page: OwnerPage, entry: FoundEntry, fields: dict[str, Any]) -> dict[str, Any]:
    stage = next(s for s in _stages(page) if s.key == entry.key)
    after = stage.after.model_copy(update=fields) if stage.after is not None else None
    return _stage_update(page, entry.key, {"after": after})


def _named(page: OwnerPage, entry: FoundEntry) -> list[Any]:
    names = page.native_names if isinstance(page, CuratedPage) else []
    return [n for n in names if not (n.text == entry.key and n.claim_id in entry.claim_ids)]


def _name_edited(page: OwnerPage, entry: FoundEntry, fields: dict[str, Any]) -> dict[str, Any]:
    names = page.native_names if isinstance(page, CuratedPage) else []
    return {
        "native_names": [
            n.model_copy(update=fields) if n.text == entry.key and n.claim_id in entry.claim_ids else n
            for n in names
        ]
    }


def _keyed_update(entries: list[Any], key: str, fields: dict[str, Any]) -> list[Any]:
    return [held.model_copy(update=fields) if held.key == key else held for held in entries]


def _keyed_without(entries: list[Any], key: str) -> list[Any]:
    return [held for held in entries if held.key != key]


def _conflicts_without(page: OwnerPage, entry: FoundEntry) -> list[Any]:
    return [c for c in page.conflicts if not (c.about == entry.key and tuple(c.claim_ids) == entry.claim_ids)]


def _conflicts_edited(page: OwnerPage, entry: FoundEntry, fields: dict[str, Any]) -> list[Any]:
    return [
        c.model_copy(update=fields) if c.about == entry.key and tuple(c.claim_ids) == entry.claim_ids else c
        for c in page.conflicts
    ]


Remover = Callable[[OwnerPage, FoundEntry], dict[str, Any]]
Editor = Callable[[OwnerPage, FoundEntry, dict[str, Any]], dict[str, Any]]

_LISTS = (_afters, _whys, _native_names, _reactions, _botanical_names, _terms, _conflicts, _questions)
_WITHOUT: Mapping[str, Remover] = MappingProxyType(
    {
        STAGE_AFTER: lambda page, entry: _stage_update(page, entry.key, {"after": None}),
        STAGE_WHY: lambda page, entry: _stage_update(page, entry.key, {"why_claim_id": None}),
        NATIVE_NAME: lambda page, entry: {"native_names": _named(page, entry)},
        REACTION: lambda page, entry: {"reactions": _keyed_without(page.reactions, entry.key)},
        BOTANICAL_NAME: lambda page, entry: _material_update(page, entry.key, {"botanical_name": None}),
        GLOSSARY_TERM: lambda page, entry: {"glossary": _keyed_without(page.glossary, entry.key)},
        CONFLICT: lambda page, entry: {"conflicts": _conflicts_without(page, entry)},
        OPEN_QUESTION: lambda page, entry: {"open_questions": _keyed_without(page.open_questions, entry.key)},
    }
)
_EDITED: Mapping[str, Editor] = MappingProxyType(
    {
        STAGE_AFTER: _after_edited,
        NATIVE_NAME: _name_edited,
        BOTANICAL_NAME: lambda page, entry, fields: _material_update(page, entry.key, fields),
        GLOSSARY_TERM: lambda page, entry, fields: {
            "glossary": _keyed_update(page.glossary, entry.key, fields)
        },
        CONFLICT: lambda page, entry, fields: {"conflicts": _conflicts_edited(page, entry, fields)},
        OPEN_QUESTION: lambda page, entry, fields: {
            "open_questions": _keyed_update(page.open_questions, entry.key, fields)
        },
    }
)
