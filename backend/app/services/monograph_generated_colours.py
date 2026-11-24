from __future__ import annotations

import re
import uuid
from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any, Protocol

from app.research.colour_key import KEY_COLOURS_MIN
from app.research.component_specs import checked_spec
from app.research.monograph_page import ComponentEntry, TextUnit
from app.research.unit_ids import KEY_UNITS

from .colour_key import KeyColour, KeyFacts, KeyText, key_colours, told_key
from .document_components import DocumentStructure
from .knowledge_view import ClaimView
from .monograph_generated_parts import RegisteredComponent
from .monograph_generated_units import DraftUnit, SubjectRecord

__all__ = [
    "COUNT_WORDS",
    "KEY_CHAPTER",
    "KEY_KICKER",
    "KEY_KIND",
    "KeyParts",
    "colour_key_label",
    "key_intro",
    "key_title",
    "place_colour_key",
]

KEY_KIND = "swatch_cards"
KEY_CHAPTER = "chem"
KEY_FIELD = "CHEMISTRY"
KEY_FIELDS = ("CHEMISTRY", "PROCESS")
LABEL_TAIL = "chemistry/colour-key"
KEY_KICKER = "Colour key"
KEY_TITLE = "{count} colours and what gives each"
KEY_DESCRIPTION = (
    "The colours the cited facts of {name} name, each beside the stage, dye or mordant that gives it, "
    "drawn as its depicted material where one shows it and named in words where none does."
)
COUNT_WORDS = ("two", "three", "four", "five", "six", "seven", "eight", "nine", "ten", "eleven", "twelve")
WEAVE = "mb-weave"
TITLE_ID = "colour-key-h"
JOIN = "becomes"
UNIT_TAG = "span"
SENTENCE_TAG = "p"
HEAD_UNITS = 3
CARD_UNITS = 6


class KeyParts(Protocol):
    @property
    def subject_slug(self) -> str: ...
    @property
    def record(self) -> SubjectRecord: ...
    @property
    def visible(self) -> Mapping[uuid.UUID, ClaimView]: ...
    @property
    def structure(self) -> DocumentStructure | None: ...
    @property
    def components(self) -> Sequence[RegisteredComponent]: ...


class KeyPage(Protocol):
    units: dict[str, TextUnit]
    drafts: dict[str, DraftUnit]
    components: dict[str, ComponentEntry]
    specs: dict[str, dict[str, Any]]
    held: dict[str, list[str]]


@dataclass
class _Held:
    page: KeyPage
    names: Iterator[str]
    refs: list[str] = field(default_factory=list)

    def label(self, text: str) -> str:
        ref = self._next()
        self.page.units[ref] = TextUnit(
            chapter=KEY_CHAPTER, tag=UNIT_TAG, field=None, nodes=[text], claim_ids=[]
        )
        return ref

    def cited(self, text: KeyText) -> str:
        ref = self._next()
        self.page.drafts[ref] = DraftUnit(ref, KEY_CHAPTER, KEY_FIELD, text.text, text.claim_ids, UNIT_TAG)
        return ref

    def _next(self) -> str:
        ref = next(self.names)
        self.refs.append(ref)
        return ref


def colour_key_label(slug: str) -> str:
    stem = re.sub(r"-+", "-", re.sub(r"[^a-z0-9-]", "", slug.lower())).strip("-")
    return f"{stem}/{LABEL_TAIL}"


def key_title(count: int) -> str:
    return KEY_TITLE.format(count=COUNT_WORDS[count - KEY_COLOURS_MIN].capitalize())


def key_intro(colours: Sequence[KeyColour]) -> str:
    names = [colour.colour.lower() for colour in colours]
    listed = f"{', '.join(names[:-1])} and {names[-1]}" if len(names) > 1 else names[0]
    return f"{listed[:1].upper()}{listed[1:]}."


def place_colour_key(parts: KeyParts, page: KeyPage, leading: dict[str, list[str]]) -> None:
    label = colour_key_label(parts.subject_slug)
    if label in page.components or any(component.kind == KEY_KIND for component in parts.components):
        return
    told = {told_key(draft.text) for draft in page.drafts.values() if draft.tag == SENTENCE_TAG}
    colours = key_colours(parts.structure, KeyFacts(parts.visible, frozenset(told)))
    if not colours:
        return
    count = HEAD_UNITS + CARD_UNITS * len(colours)
    held = _Held(page, iter(KEY_UNITS.fresh(count, {*page.units, *page.drafts})))
    title = key_title(len(colours))
    spec = {
        "chapterNo": held.label(KEY_KICKER),
        "title": held.label(title),
        "titleId": TITLE_ID,
        "intro": held.label(key_intro(colours)),
        "weave": WEAVE,
        "colours": [_card(colour, held) for colour in colours],
    }
    page.specs[label] = checked_spec(KEY_KIND, spec).model_dump(mode="json", by_alias=True)
    page.components[label] = _entry(label, parts, title)
    page.held[label] = held.refs
    leading.setdefault(KEY_CHAPTER, []).insert(0, label)


def _card(colour: KeyColour, held: _Held) -> dict[str, Any]:
    card: dict[str, Any] = {}
    if colour.dye is not None:
        if colour.before_dye is not None and colour.before is not None:
            card["before"] = {"dye": colour.before_dye, "caption": held.label(colour.before.capitalize())}
            card["join"] = JOIN
        card["after"] = {"dye": colour.dye, "caption": held.label(colour.caption)}
    card["name"] = held.label(colour.colour.capitalize())
    card["agent"] = held.label(colour.agent)
    card["text"] = held.cited(colour.text)
    if colour.why is not None:
        card["why"] = held.cited(colour.why)
    return card


def _entry(label: str, parts: KeyParts, title: str) -> ComponentEntry:
    return ComponentEntry(
        label=label,
        chapter=KEY_CHAPTER,
        anchor="#" + label.replace("/", "--"),
        kind=KEY_KIND,
        title=title,
        description=KEY_DESCRIPTION.format(name=parts.record.name),
        field=KEY_FIELD,
        fields=list(KEY_FIELDS),
        subjects=[f"craft:{parts.subject_slug}"],
    )
