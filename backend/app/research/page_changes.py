from __future__ import annotations

import json
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Any, Literal

from pydantic import Field

from .base import ContractModel, absent
from .chapter_keys import CHAPTER_TITLES
from .monograph_document import MonographDocument
from .page_report_rules import OPENING, PICTURE_KIND, ReadPage, node_text

__all__ = [
    "ADDED",
    "CHANGED",
    "CHANGES_SHOWN_MAX",
    "CHANGE_KINDS",
    "CHANGE_MARKS",
    "COMPONENT_CHANGE",
    "PICTURE_CHANGE",
    "REMOVED",
    "SENTENCE_CHANGE",
    "TEXT_MAX_CHARS",
    "ChangeCount",
    "ChapterChanges",
    "PageChange",
    "chapter_title",
    "page_changes",
]

CHANGE_MARKS = ("ADDED", "CHANGED", "REMOVED")
CHANGE_KINDS = ("SENTENCE", "COMPONENT", "PICTURE")
ADDED, CHANGED, REMOVED = CHANGE_MARKS
SENTENCE_CHANGE, COMPONENT_CHANGE, PICTURE_CHANGE = CHANGE_KINDS
TEXT_MAX_CHARS = 400
CHANGES_SHOWN_MAX = 60
OPENING_TITLE = "The opening"
PLACE_WORDS = "its place"
ELLIPSIS = "…"

ChangeMark = Literal[*CHANGE_MARKS]
ChangeKind = Literal[*CHANGE_KINDS]


class PageChange(ContractModel):
    kind: ChangeKind
    change: ChangeMark
    ref: str
    before: str | None = None
    after: str | None = None
    component_kind: str | None = Field(default=None, exclude_if=absent)
    moved_from: str | None = Field(default=None, exclude_if=absent)


class ChangeCount(ContractModel):
    added: int = Field(default=0, ge=0)
    changed: int = Field(default=0, ge=0)
    removed: int = Field(default=0, ge=0)


class ChapterChanges(ContractModel):
    key: str
    title: str
    sentences: ChangeCount
    components: ChangeCount
    pictures: ChangeCount
    changes: list[PageChange] = Field(max_length=CHANGES_SHOWN_MAX)


@dataclass(frozen=True)
class _Piece:
    chapter: str
    text: str
    stamp: str
    kind: str | None = None


@dataclass(frozen=True)
class _Read:
    sentences: Mapping[str, _Piece]
    components: Mapping[str, _Piece]
    pictures: Mapping[str, _Piece]
    chapters: tuple[str, ...]


def page_changes(before: MonographDocument | None, after: MonographDocument) -> list[ChapterChanges]:
    old, new = _read(before), _read(after)
    keys = dict.fromkeys((*new.chapters, *old.chapters))
    found = [_chapter(key, chapter_title(key, after, before), old, new) for key in keys]
    return [chapter for chapter in found if chapter.changes]


def chapter_title(key: str, *documents: MonographDocument | None) -> str:
    for document in documents:
        if document is None:
            continue
        for named in document.content.chapters:
            if named.key == key:
                return named.title
    if key == OPENING:
        return OPENING_TITLE
    return CHAPTER_TITLES.get(key, key).replace("{place}", PLACE_WORDS)


def _chapter(key: str, title: str, old: _Read, new: _Read) -> ChapterChanges:
    sentences = _changes(SENTENCE_CHANGE, key, old.sentences, new.sentences)
    components = _changes(COMPONENT_CHANGE, key, old.components, new.components)
    pictures = _changes(PICTURE_CHANGE, key, old.pictures, new.pictures)
    return ChapterChanges(
        key=key,
        title=title,
        sentences=_counted(sentences),
        components=_counted(components),
        pictures=_counted(pictures),
        changes=[*components, *pictures, *sentences][:CHANGES_SHOWN_MAX],
    )


def _changes(
    kind: str, chapter: str, old: Mapping[str, _Piece], new: Mapping[str, _Piece]
) -> list[PageChange]:
    found: list[PageChange] = []
    for ref, piece in new.items():
        was = old.get(ref)
        if piece.chapter != chapter or (
            was is not None and was.stamp == piece.stamp and was.chapter == chapter
        ):
            continue
        found.append(_made(kind, ref, was, piece, chapter))
    for ref, was in old.items():
        if was.chapter == chapter and ref not in new:
            found.append(_change(kind, REMOVED, ref, before=was.text, kind_of=was.kind))
    return found


def _made(kind: str, ref: str, was: _Piece | None, piece: _Piece, chapter: str) -> PageChange:
    if was is None:
        return _change(kind, ADDED, ref, after=piece.text, kind_of=piece.kind)
    moved = was.chapter if was.chapter != chapter else None
    change = _change(kind, CHANGED, ref, before=was.text, after=piece.text, kind_of=piece.kind)
    return change.model_copy(update={"moved_from": moved})


def _change(
    kind: str,
    change: str,
    ref: str,
    *,
    before: str | None = None,
    after: str | None = None,
    kind_of: str | None = None,
) -> PageChange:
    return PageChange.model_validate(
        {
            "kind": kind,
            "change": change,
            "ref": ref,
            "before": before,
            "after": after,
            "componentKind": kind_of,
        }
    )


def _counted(changes: Iterable[PageChange]) -> ChangeCount:
    marks = [change.change for change in changes]
    return ChangeCount(added=marks.count(ADDED), changed=marks.count(CHANGED), removed=marks.count(REMOVED))


def _read(document: MonographDocument | None) -> _Read:
    if document is None:
        return _Read({}, {}, {}, ())
    content = document.content
    placed = [entry.ref for entry in content.layout if entry.kind == "unit" and entry.within is None]
    sentences = {
        ref: _Piece(unit.chapter, _shown(text), text)
        for ref in placed
        if (unit := content.units.get(ref)) is not None
        and unit.claim_ids
        and (text := " ".join(node_text(unit.nodes).split()))
    }
    page = ReadPage.of(document)
    components = {
        entry.label: _Piece(
            entry.chapter, entry.title, _stamp(document, entry.label, entry.title), entry.kind
        )
        for entry in content.components
        if entry.kind != PICTURE_KIND
    }
    pictures = {entry.label: _picture(page, entry.label, entry.chapter) for entry in page.pictures}
    chapters = tuple(dict.fromkeys(entry.chapter for entry in content.layout))
    return _Read(sentences, components, pictures, chapters)


def _picture(page: ReadPage, label: str, chapter: str) -> _Piece:
    src, caption, credit = page.plate(label)
    shown = caption or src or label
    return _Piece(chapter, _shown(shown), json.dumps([src, caption, credit]), PICTURE_KIND)


def _stamp(document: MonographDocument, label: str, title: str) -> str:
    units = document.content.units
    held = [
        node_text(unit.nodes)
        for entry in document.content.layout
        if entry.within == label and (unit := units.get(entry.ref)) is not None
    ]
    spec = _resolved(document.specs.get(label, {}), units)
    return json.dumps([title, spec, held], sort_keys=True, ensure_ascii=False)


def _resolved(value: Any, units: Mapping[str, Any]) -> Any:
    if isinstance(value, str):
        unit = units.get(value)
        return value if unit is None else node_text(unit.nodes)
    if isinstance(value, Mapping):
        return {key: _resolved(item, units) for key, item in value.items()}
    if isinstance(value, list):
        return [_resolved(item, units) for item in value]
    return value


def _shown(text: str) -> str:
    return text if len(text) <= TEXT_MAX_CHARS else text[: TEXT_MAX_CHARS - 1].rstrip() + ELLIPSIS
