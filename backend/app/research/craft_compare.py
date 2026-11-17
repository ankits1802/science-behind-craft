from __future__ import annotations

import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal, Self

from pydantic import Field, model_validator

from .base import ContractModel
from .blocks_learning import (
    COMPARE_CRAFTS_MAX,
    COMPARE_CRAFTS_MIN,
    COMPARE_ROWS_MAX,
    CompareBlock,
    CompareCell,
    CompareRow,
    CompareTerm,
)
from .citations import SourceRef, cited_source_ids
from .crafts import CraftRef
from .offered_facts import OfferedFact, first_naming, shown_sentence, term_marker

__all__ = [
    "COMPARE_BLOCK_ID",
    "COMPARE_SCHEMA_VERSION",
    "COMPARE_TERM_ROWS_MAX",
    "CraftComparison",
    "CraftFacts",
    "SharedTerm",
    "compare_block",
]

COMPARE_SCHEMA_VERSION = 1
COMPARE_BLOCK_ID = "compare"
COMPARE_TERM_ROWS_MAX = 3


@dataclass(frozen=True)
class SharedTerm:
    key: str
    label: str
    surfaces: tuple[str, ...]
    concept_ids: frozenset[uuid.UUID] = frozenset()


@dataclass(frozen=True)
class CraftFacts:
    craft: CraftRef
    facts: tuple[OfferedFact, ...]


@dataclass(frozen=True)
class _Row:
    facet: str
    term: SharedTerm | None
    cells: tuple[OfferedFact | None, ...]


class CraftComparison(ContractModel):
    schema_version: Literal[1]
    comparison: CompareBlock
    sources: list[SourceRef] = Field(min_length=1)

    @model_validator(mode="after")
    def _sources_as_cited(self) -> Self:
        if [source.id for source in self.sources] != cited_source_ids(self.comparison.cited_sentences()):
            raise ValueError("a comparison lists every source it cites once, in order of first citation")
        return self


def compare_block(
    crafts: Sequence[CraftFacts],
    terms: Sequence[SharedTerm],
    *,
    facets: Sequence[str],
    block_id: str,
    rows_max: int = COMPARE_ROWS_MAX,
) -> CompareBlock | None:
    slugs = {entry.craft.slug for entry in crafts}
    if len(slugs) != len(crafts) or not COMPARE_CRAFTS_MIN <= len(crafts) <= COMPARE_CRAFTS_MAX:
        return None
    rows: list[_Row] = []
    shown: set[str] = set()
    for facet in dict.fromkeys(facets):
        for row in _facet_rows(crafts, terms, facet, shown):
            if len(rows) < rows_max:
                rows.append(row)
                shown.update(claim for cell in row.cells if cell is not None for claim in cell.claim_ids)
    if not rows:
        return None
    return CompareBlock(
        id=block_id,
        kind="compare",
        version=1,
        reuse=None,
        crafts=[entry.craft for entry in crafts],
        rows=[_shown_row(row, f"{block_id}.r{number}") for number, row in enumerate(rows, start=1)],
    )


def _facet_rows(
    crafts: Sequence[CraftFacts], terms: Sequence[SharedTerm], facet: str, shown: set[str]
) -> list[_Row]:
    taken = set(shown)
    rows: list[_Row] = []
    for term in terms:
        if sum(1 for row in rows if row.term is not None) == COMPARE_TERM_ROWS_MAX:
            break
        row = _row(crafts, facet, term, taken)
        if row is not None:
            rows.append(row)
            taken.update(claim for cell in row.cells if cell is not None for claim in cell.claim_ids)
    plain = _row(crafts, facet, None, taken)
    return [*rows, plain] if plain is not None else rows


def _row(crafts: Sequence[CraftFacts], facet: str, term: SharedTerm | None, taken: set[str]) -> _Row | None:
    avoiding = frozenset(taken)
    cells: list[OfferedFact | None] = []
    for entry in crafts:
        facts = [fact for fact in entry.facts if fact.facet == facet]
        cell = _cell(facts, term, avoiding)
        cells.append(cell)
        if cell is not None:
            avoiding |= cell.claim_ids
    if sum(1 for cell in cells if cell is not None) < COMPARE_CRAFTS_MIN:
        return None
    return _Row(facet, term, tuple(cells))


def _cell(
    facts: Sequence[OfferedFact], term: SharedTerm | None, avoiding: frozenset[str]
) -> OfferedFact | None:
    if term is not None:
        about = [fact for fact in facts if fact.concept_id in term.concept_ids]
        return first_naming(about, term.label, avoiding=avoiding) or first_naming(
            facts, term.label, avoiding=avoiding
        )
    return next((f for f in sorted(facts, key=lambda fact: fact.rank) if not f.claim_ids & avoiding), None)


def _shown_row(row: _Row, prefix: str) -> CompareRow:
    marker = term_marker(row.term.key, row.term.surfaces) if row.term is not None else None
    return CompareRow(
        facet=row.facet,
        term=CompareTerm(key=row.term.key, label=row.term.label) if row.term is not None else None,
        cells=[
            None
            if cell is None
            else CompareCell(
                sentence=shown_sentence(cell, f"{prefix}.{number}", marker), piece_id=cell.piece_id
            )
            for number, cell in enumerate(row.cells, start=1)
        ],
    )
