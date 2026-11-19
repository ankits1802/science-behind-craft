from __future__ import annotations

import uuid
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any

from app.research.chapter_keys import CHAPTER_KEYS, DISCIPLINE_CHAPTERS
from app.research.monograph_document import MonographDocument
from app.research.monograph_page import CitedSource, ComponentEntry, LayoutEntry, MonographContent, TextUnit
from app.research.page_layout import PageLayout, PageLayoutEntry, arranged_layout, picture_label

from .knowledge_view import ClaimView
from .monograph_generated_drawings import Drawings
from .monograph_generated_parts import PlacedPicture, RegisteredComponent, StoredSection
from .monograph_generated_units import (
    MASTHEAD_CHAPTER,
    DraftUnit,
    SourceBook,
    SubjectRecord,
    cited_unit,
    heading_unit,
    masthead_units,
    section_units,
)
from .page_layouts_backfill import LEADING_ROLES, picture_placement

__all__ = ["LAYOUT_DATA", "GeneratedParts", "assembled_document"]

LAYOUT_DATA = "page-layout"
PICTURE_KIND = "picture_plate"
HERO = "HERO"
CRAFT_SUBJECTS = frozenset({"craft", "family"})
DEFAULT_FIELD = "OVERVIEW"
CHAPTER_FIELDS: Mapping[str, str] = MappingProxyType(
    {
        chapter: next((f for f, c in DISCIPLINE_CHAPTERS.items() if c == chapter), DEFAULT_FIELD)
        for chapter in CHAPTER_KEYS
    }
)


@dataclass(frozen=True)
class GeneratedParts:
    subject_kind: str
    subject_slug: str
    page_url: str
    record: SubjectRecord
    sections: tuple[StoredSection, ...]
    visible: Mapping[uuid.UUID, ClaimView]
    sources: Mapping[str, CitedSource]
    components: tuple[RegisteredComponent, ...] = ()
    pictures: tuple[PlacedPicture, ...] = ()
    layout: PageLayout | None = None


@dataclass
class _Page:
    units: dict[str, TextUnit] = field(default_factory=dict)
    drafts: dict[str, DraftUnit] = field(default_factory=dict)
    components: dict[str, ComponentEntry] = field(default_factory=dict)
    specs: dict[str, dict[str, Any]] = field(default_factory=dict)
    fragments: dict[str, str] = field(default_factory=dict)
    reused: dict[str, str] = field(default_factory=dict)
    default: list[LayoutEntry] = field(default_factory=list)


def assembled_document(parts: GeneratedParts, drawings: Drawings) -> MonographDocument | None:
    page = _Page()
    texts = _texts(parts, page)
    if not page.drafts:
        return None
    pictures = _pictures(parts, page)
    components = _components(parts, page, drawings)
    _lay_out(parts, page, (texts, pictures, components))
    arranged = arranged_layout(page.default, parts.layout)
    book = SourceBook()
    citations, claims = _cite(parts, page, arranged, book)
    for label, monograph in page.reused.items():
        filled = drawings.fragment(monograph, label, book)
        page.fragments[label] = filled.markup
        citations.update(filled.citations)
        claims.update(filled.citation_claims)
    content = MonographContent(
        craft_slug=parts.subject_slug,
        sources=book.sources,
        citations=citations,
        citation_claims=claims,
        data={LAYOUT_DATA: parts.layout.model_dump(mode="json", by_alias=True)} if parts.layout else {},
        units=page.units,
        components=[page.components[e.ref] for e in arranged if e.kind == "component"],
        layout=arranged,
    )
    return MonographDocument(
        subject_kind=parts.subject_kind,
        subject_slug=parts.subject_slug,
        title=parts.record.name,
        version=sum(section.version for section in parts.sections),
        content=content,
        specs=page.specs,
        fragments=page.fragments,
        page_url=parts.page_url,
    )


def _texts(parts: GeneratedParts, page: _Page) -> dict[str, list[str]]:
    taken: set[str] = set()
    by_chapter: dict[str, list[str]] = {}
    for section in parts.sections:
        drafts = section_units(section.field, section.sentences, parts.visible, taken)
        if not drafts:
            continue
        heading_id, heading = heading_unit(section.field)
        page.units[heading_id] = heading
        refs = by_chapter.setdefault(heading.chapter, [])
        refs.append(heading_id)
        for draft in drafts:
            page.drafts[draft.unit_id] = draft
            refs.append(draft.unit_id)
    return by_chapter


def _pictures(parts: GeneratedParts, page: _Page) -> dict[str, list[str]]:
    by_chapter: dict[str, list[tuple[bool, str]]] = {}
    for placed in parts.pictures:
        label = picture_label(parts.subject_slug, placed.picture.key)
        chapter, role = picture_placement(placed.picture)
        entry = parts.layout.entry(label) if parts.layout is not None else None
        role = entry.role if entry is not None else role
        page.components[label] = _picture_entry(parts, placed, label, chapter)
        page.specs[label] = _picture_spec(placed, role, entry)
        by_chapter.setdefault(chapter, []).append((role not in LEADING_ROLES, label))
    return {
        chapter: [label for _, label in sorted(found, key=lambda item: item[0])]
        for chapter, found in by_chapter.items()
    }


def _components(parts: GeneratedParts, page: _Page, drawings: Drawings) -> dict[str, list[str]]:
    by_chapter: dict[str, list[str]] = {}
    for component in parts.components:
        if component.label in page.components or component.monograph is None:
            continue
        spec = drawings.spec(component.monograph, component.label)
        if spec is not None:
            page.specs[component.label] = spec
        elif drawings.has_fragment(component.monograph, component.label):
            page.reused[component.label] = component.monograph
        else:
            continue
        chapter = DISCIPLINE_CHAPTERS[component.field]
        page.components[component.label] = ComponentEntry(
            label=component.label,
            chapter=chapter,
            anchor=component.anchor or _anchor(component.label),
            kind=component.kind,
            title=component.title,
            description=component.description,
            field=component.field,
            fields=list(component.fields),
            subjects=list(component.subjects),
        )
        by_chapter.setdefault(chapter, []).append(component.label)
    return by_chapter


def _lay_out(parts: GeneratedParts, page: _Page, found: Sequence[Mapping[str, list[str]]]) -> None:
    texts, pictures, components = found
    masthead = masthead_units(parts.record)
    page.units.update(masthead)
    hero = next((label for label, spec in page.specs.items() if spec.get("role") == HERO), None)
    for chapter in CHAPTER_KEYS:
        refs = [*pictures.get(chapter, []), *texts.get(chapter, [])]
        if chapter == MASTHEAD_CHAPTER:
            within = hero if hero in refs else None
            heads = [hero] if within is not None else []
            rest = [ref for ref in refs if ref != within]
            page.default += [_entry(chapter, ref, None, page) for ref in heads]
            page.default += [_entry(chapter, ref, within, page) for ref in masthead]
            refs = rest
        page.default += [_entry(chapter, ref, None, page) for ref in refs]
        page.default += [_entry(chapter, ref, None, page) for ref in components.get(chapter, [])]


def _entry(chapter: str, ref: str, within: str | None, page: _Page) -> LayoutEntry:
    kind = "component" if ref in page.components else "unit"
    return LayoutEntry(chapter=chapter, kind=kind, ref=ref, within=within)


def _cite(
    parts: GeneratedParts, page: _Page, arranged: Sequence[LayoutEntry], book: SourceBook
) -> tuple[dict[str, Any], dict[str, list[str]]]:
    citations: dict[str, Any] = {}
    claims: dict[str, list[str]] = {}
    for entry in arranged:
        if entry.kind == "component":
            settled = page.components[entry.ref].model_copy(update={"chapter": entry.chapter})
            page.components[entry.ref] = settled
            continue
        draft = page.drafts.get(entry.ref)
        if draft is None:
            page.units[entry.ref] = page.units[entry.ref].model_copy(update={"chapter": entry.chapter})
            continue
        unit, quotes = cited_unit(draft, parts.visible, book, parts.sources)
        page.units[entry.ref] = unit.model_copy(update={"chapter": entry.chapter})
        if quotes:
            citations[entry.ref] = quotes
            claims[entry.ref] = list(unit.claim_ids)
    return citations, claims


def _picture_entry(parts: GeneratedParts, placed: PlacedPicture, label: str, chapter: str) -> ComponentEntry:
    picture, media = placed.picture, placed.media
    credit = ", ".join(part for part in (media.author, media.licence) if part)
    return ComponentEntry(
        label=label,
        chapter=chapter,
        anchor=_anchor(label),
        kind=PICTURE_KIND,
        title=picture.caption,
        description=f"A picture for {parts.record.name}: {picture.caption}"
        + (f" ({credit})." if credit else "."),
        field=CHAPTER_FIELDS.get(chapter, DEFAULT_FIELD),
        fields=[],
        subjects=[f"craft:{parts.subject_slug}"] if parts.subject_kind in CRAFT_SUBJECTS else [],
    )


def _picture_spec(placed: PlacedPicture, role: str, entry: PageLayoutEntry | None) -> dict[str, Any]:
    picture = placed.picture
    crop = entry.crop if entry is not None and entry.crop is not None else picture.focal
    return {
        "media": placed.media.model_dump(mode="json", by_alias=True),
        "caption": entry.caption if entry is not None and entry.caption else picture.caption,
        "standIn": picture.stand_in,
        "focal": crop.model_dump(mode="json", by_alias=True) if crop is not None else None,
        "role": role,
        "size": entry.size if entry is not None else None,
        "claimIds": [str(claim_id) for claim_id in picture.claim_ids],
    }


def _anchor(label: str) -> str:
    return "#" + label.replace("/", "--")
