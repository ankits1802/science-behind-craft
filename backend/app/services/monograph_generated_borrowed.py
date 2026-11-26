from __future__ import annotations

from typing import Any, Protocol

from app.core.errors import InvalidInput
from app.research.monograph_page import ComponentEntry, TextUnit

from .document_components_data import (
    READER_SCOPE,
    fragment_sentences,
    kit_data,
    merged_data,
    monograph_data,
    reader_data,
    unit_sentences,
)
from .document_components_homes import home_scopes
from .monograph_generated_drawings import Drawings, spec_unit_keys
from .monograph_generated_units import SourceBook

__all__ = ["BorrowingPage", "borrow_drawn"]


class BorrowingPage(Protocol):
    units: dict[str, TextUnit]
    components: dict[str, ComponentEntry]
    specs: dict[str, dict[str, Any]]
    fragments: dict[str, str]
    reused: dict[str, str]
    borrowed_specs: dict[str, str]
    data: dict[str, Any]


def borrow_drawn(
    page: BorrowingPage,
    drawings: Drawings,
    book: SourceBook,
    citations: dict[str, Any],
    claims: dict[str, list[str]],
) -> None:
    for label, monograph in page.reused.items():
        filled = drawings.fragment(monograph, label, book)
        page.fragments[label] = filled.markup
        citations.update(filled.citations)
        claims.update(filled.citation_claims)
    for label, monograph in page.borrowed_specs.items():
        cited = drawings.spec_cites(monograph, page.specs[label], book)
        page.specs[label] = cited.spec
        citations.update(cited.citations)
        claims.update(cited.citation_claims)
        named = drawings.spec_units(monograph, page.specs[label], book)
        for key, unit in named.units.items():
            if page.units.get(key, unit) != unit:
                raise InvalidInput(f"The spec of {label} names unit {key}, which this page already holds")
            page.units[key] = unit
        citations.update(named.citations)
        claims.update(named.citation_claims)
    _borrow_data(page, drawings, book)


def _borrow_data(page: BorrowingPage, drawings: Drawings, book: SourceBook) -> None:
    read: dict[str, dict[str, Any]] = {}
    for label, monograph in {**page.reused, **page.borrowed_specs}.items():
        if monograph not in read:
            read[monograph] = monograph_data(drawings.root, monograph)
        found = kit_data(read[monograph], page.components[label].kind, page.specs.get(label))
        merged_data(page.data, found)
        if home_scopes(monograph).get(label) == READER_SCOPE:
            numbers = drawings.source_numbers(monograph, book)
            merged_data(page.data, reader_data(read[monograph], _held_sentences(page, label), numbers))


def _held_sentences(page: BorrowingPage, label: str) -> set[str]:
    if label in page.fragments:
        return fragment_sentences(page.fragments[label])
    named = spec_unit_keys(page.specs.get(label, {}))
    return unit_sentences(page.units[key].nodes for key in sorted(named) if key in page.units)
