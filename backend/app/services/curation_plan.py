from __future__ import annotations

import uuid
from collections.abc import Mapping
from dataclasses import dataclass, replace
from typing import Any

from app.curation.check_file import CheckFile
from app.curation.dossier import Dossier
from app.data.district_register import DistrictCodes

from .curated_index import CuratedPage
from .curation_page_index import curated_page_index
from .curation_records import (
    gi_row,
    media_claim_rows,
    media_rows,
    price_rows,
    term_link_rows,
    term_rows,
    workforce_rows,
)
from .curation_rows import (
    ConceptPlan,
    CraftTarget,
    claim_rows,
    claim_source_rows,
    concept_plan,
    curated_claim_rows,
    source_rows,
)
from .curation_structure import (
    location_rows,
    material_rows,
    process_row,
    reaction_citation_rows,
    reaction_rows,
    stage_material_rows,
    stage_rows,
)

__all__ = ["PLAN_PARTS", "SOURCE_REFERENCES", "CurationPlan", "curation_plan"]

PLAN_PARTS = (
    "sources",
    "concepts",
    "claims",
    "curatedClaims",
    "claimSources",
    "locations",
    "processes",
    "stages",
    "materials",
    "stageMaterials",
    "reactions",
    "reactionCitations",
    "media",
    "mediaClaims",
    "terms",
    "termCrafts",
    "termConcepts",
    "giRecords",
    "prices",
    "workforce",
)
SOURCE_REFERENCES = (("claimSources", "sourceId"), ("locations", "sourceId"))

Rows = tuple[dict[str, Any], ...]


@dataclass(frozen=True)
class CurationPlan:
    craft: CraftTarget
    dossier: Dossier
    concepts: ConceptPlan
    rows: Mapping[str, Rows]
    index: CuratedPage

    def part(self, name: str) -> Rows:
        return self.rows[name]

    def claim_ids(self) -> list[uuid.UUID]:
        return [row["id"] for row in self.rows["claims"]]

    def with_sources(self, aliases: Mapping[uuid.UUID, uuid.UUID]) -> CurationPlan:
        if not aliases:
            return self
        rows = dict(self.rows)
        rows["sources"] = tuple(row for row in rows["sources"] if row["id"] not in aliases)
        for part, column in SOURCE_REFERENCES:
            rows[part] = tuple({**row, column: aliases.get(row[column], row[column])} for row in rows[part])
        return replace(self, rows=rows)


def curation_plan(
    dossier: Dossier, check: CheckFile, craft: CraftTarget, codes: DistrictCodes
) -> CurationPlan:
    concepts = concept_plan(dossier, craft)
    locations = location_rows(dossier, craft, codes)
    terms_to_crafts, terms_to_concepts = term_link_rows(dossier, craft, concepts)
    process = process_row(dossier, craft)
    gi = gi_row(dossier, craft)
    found: dict[str, list[dict[str, Any]]] = {
        "sources": source_rows(dossier, check),
        "concepts": list(concepts.rows),
        "claims": claim_rows(dossier, check, concepts),
        "curatedClaims": curated_claim_rows(dossier, craft),
        "claimSources": claim_source_rows(dossier, check),
        "locations": locations,
        "processes": [process] if process else [],
        "stages": stage_rows(dossier, concepts),
        "materials": material_rows(dossier, concepts),
        "stageMaterials": stage_material_rows(dossier),
        "reactions": reaction_rows(dossier),
        "reactionCitations": reaction_citation_rows(dossier),
        "media": media_rows(dossier),
        "mediaClaims": media_claim_rows(dossier),
        "terms": term_rows(dossier),
        "termCrafts": terms_to_crafts,
        "termConcepts": terms_to_concepts,
        "giRecords": [gi] if gi else [],
        "prices": price_rows(dossier, craft, codes),
        "workforce": workforce_rows(dossier, craft),
    }
    index = curated_page_index(dossier, concepts, codes, {row["id"] for row in locations})
    rows = {name: tuple(found[name]) for name in PLAN_PARTS}
    return CurationPlan(craft=craft, dossier=dossier, concepts=concepts, rows=rows, index=index)
