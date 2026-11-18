from __future__ import annotations

import uuid
from collections.abc import Mapping
from dataclasses import dataclass, replace
from typing import Any

from app.core.errors import InvalidInput
from app.curation.check_file import CheckFile
from app.curation.dossier import CATEGORY_SCOPE, Dossier

from .curated_category_index import CuratedCategoryPage, category_index
from .curation_plan import Rows, aliased_sources
from .curation_records import media_claim_rows, media_rows, term_concept_rows, term_rows
from .curation_rows import (
    ConceptPlan,
    claim_rows,
    claim_source_rows,
    concept_plan,
    curated_claim_rows,
    source_rows,
)

__all__ = ["CATEGORY_OWNER_COLUMN", "CATEGORY_PLAN_PARTS", "CategoryPlan", "CategoryTarget", "category_plan"]

CATEGORY_OWNER_COLUMN = "categoryId"
CATEGORY_PLAN_PARTS = (
    "sources",
    "concepts",
    "claims",
    "curatedClaims",
    "claimSources",
    "media",
    "mediaClaims",
    "terms",
    "termConcepts",
)


@dataclass(frozen=True)
class CategoryTarget:
    id: uuid.UUID
    slug: str
    name: str


@dataclass(frozen=True)
class CategoryPlan:
    category: CategoryTarget
    dossier: Dossier
    concepts: ConceptPlan
    rows: Mapping[str, Rows]
    index: CuratedCategoryPage

    def part(self, name: str) -> Rows:
        return self.rows[name]

    def claim_ids(self) -> list[uuid.UUID]:
        return [row["id"] for row in self.rows["claims"]]

    def with_sources(self, aliases: Mapping[uuid.UUID, uuid.UUID]) -> CategoryPlan:
        if not aliases:
            return self
        return replace(self, rows=aliased_sources(self.rows, aliases))


def category_plan(dossier: Dossier, check: CheckFile, category: CategoryTarget) -> CategoryPlan:
    if dossier.scope != CATEGORY_SCOPE or dossier.slug != category.slug:
        raise InvalidInput(f"the dossier of {dossier.slug} is not the category dossier of {category.slug}")
    concepts = concept_plan(dossier, craft_id=None, name=category.name)
    found: dict[str, list[dict[str, Any]]] = {
        "sources": source_rows(dossier, check),
        "concepts": list(concepts.rows),
        "claims": claim_rows(dossier, check, concepts),
        "curatedClaims": curated_claim_rows(dossier, CATEGORY_OWNER_COLUMN, category.id),
        "claimSources": claim_source_rows(dossier, check),
        "media": media_rows(dossier),
        "mediaClaims": media_claim_rows(dossier),
        "terms": term_rows(dossier),
        "termConcepts": term_concept_rows(dossier, concepts),
    }
    rows = {name: tuple(found[name]) for name in CATEGORY_PLAN_PARTS}
    return CategoryPlan(
        category=category,
        dossier=dossier,
        concepts=concepts,
        rows=rows,
        index=category_index(dossier, concepts),
    )
