from __future__ import annotations

import logging
import uuid
from collections.abc import Mapping
from typing import Any, Literal

from pydantic import AwareDatetime, Field, ValidationError

from app.curation.dossier import Dossier
from app.models.enums import COVERAGE_CLASSES
from app.research.base import ContractModel

from .curated_index import (
    IndexConflict,
    IndexMaterial,
    IndexOverview,
    IndexPicture,
    IndexQuestion,
    IndexReaction,
    IndexSearch,
    IndexTerm,
)
from .curation_keys import curated_id
from .curation_overview import OverviewPieces, placed_overview
from .curation_page_index import (
    index_category_reactions,
    index_conflicts,
    index_glossary,
    index_key_facts,
    index_pictures,
)
from .curation_rows import ConceptPlan

__all__ = [
    "CURATED_CATEGORY_SCHEMA_VERSION",
    "CuratedCategoryPage",
    "IndexCategoryQuestion",
    "IndexSentenceRefs",
    "category_index",
    "indexed_category_overview",
    "stored_category_page",
]

logger = logging.getLogger(__name__)

CURATED_CATEGORY_SCHEMA_VERSION = 1


class IndexSentenceRefs(ContractModel):
    sentence_id: str = Field(min_length=1)
    sub_categories: list[str]
    crafts: list[str]


class IndexCategoryQuestion(IndexQuestion):
    sub_categories: list[str]


class CuratedCategoryPage(ContractModel):
    schema_version: Literal[1] = CURATED_CATEGORY_SCHEMA_VERSION
    category_slug: str
    version: int = Field(ge=1)
    curated_at: AwareDatetime
    coverage: Literal[*COVERAGE_CLASSES]
    searched: list[IndexSearch]
    overview: IndexOverview
    sentence_refs: list[IndexSentenceRefs]
    conflicts: list[IndexConflict]
    open_questions: list[IndexCategoryQuestion]
    glossary: list[IndexTerm]
    pictures: list[IndexPicture]
    materials: list[IndexMaterial] = Field(default_factory=list)
    reactions: list[IndexReaction] = Field(default_factory=list)

    def piece_ids(self) -> dict[str, uuid.UUID]:
        return self.overview.piece_ids()

    def refs(self) -> dict[str, IndexSentenceRefs]:
        return {ref.sentence_id: ref for ref in self.sentence_refs}


def category_index(dossier: Dossier, concepts: ConceptPlan) -> CuratedCategoryPage:
    return CuratedCategoryPage(
        category_slug=dossier.slug,
        version=dossier.version,
        curated_at=dossier.curated_at,
        coverage=dossier.coverage,
        searched=[IndexSearch(query=item.query, site=item.site) for item in dossier.searched],
        overview=IndexOverview(key_facts=index_key_facts(dossier)),
        sentence_refs=[],
        conflicts=index_conflicts(dossier),
        open_questions=_questions(dossier),
        glossary=index_glossary(dossier, concepts),
        pictures=index_pictures(dossier),
        reactions=index_category_reactions(dossier),
    )


def _questions(dossier: Dossier) -> list[IndexCategoryQuestion]:
    return [
        IndexCategoryQuestion(
            key=item.id,
            question=item.question,
            settled_by=item.settled_by,
            claim_ids=[curated_id(dossier.slug, claim_id) for claim_id in item.claim_ids],
            sub_categories=list(item.sub_categories),
        )
        for item in dossier.open_questions
    ]


def indexed_category_overview(index: CuratedCategoryPage, overview: OverviewPieces) -> CuratedCategoryPage:
    refs = [
        IndexSentenceRefs(
            sentence_id=sentence_id,
            sub_categories=list(sentence.sub_categories),
            crafts=list(sentence.crafts),
        )
        for sentence_id, sentence in overview.sentences.items()
        if sentence.sub_categories or sentence.crafts
    ]
    placed = placed_overview(index.overview.key_facts, overview)
    return index.model_copy(update={"overview": placed, "sentence_refs": refs})


def stored_category_page(
    category_id: uuid.UUID, page: Mapping[str, Any] | None
) -> CuratedCategoryPage | None:
    if page is None:
        return None
    try:
        return CuratedCategoryPage.model_validate(page)
    except ValidationError:
        logger.warning("category %s has a curated page index that no longer meets its model", category_id)
        return None
