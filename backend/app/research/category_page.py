from __future__ import annotations

import json
import uuid
from collections import Counter
from collections.abc import Iterator, Sequence
from typing import Literal, Self

from pydantic import AwareDatetime, Field, model_validator

from app.models.enums import COVERAGE_CLASSES, GI_STATUSES

from .base import ContractModel
from .citations import AnswerSentence, Citation, SourceRef
from .crafts import SLUG_MAX_CHARS, CraftRef
from .media_refs import MediaRef
from .terms import TermSpan
from .vocabulary import Discipline, EvidenceLevel

__all__ = [
    "CATEGORY_LIST_SCHEMA_VERSION",
    "CATEGORY_PAGE_SCHEMA_VERSION",
    "CategoryClaim",
    "CategoryCuration",
    "CategoryDiffer",
    "CategoryFact",
    "CategoryHero",
    "CategoryList",
    "CategoryOverview",
    "CategoryPage",
    "CategoryPicture",
    "CategoryQuestion",
    "CategoryRef",
    "CategorySearch",
    "CategorySection",
    "CategorySentence",
    "CategorySubCategory",
    "CategorySummary",
    "CategoryTerm",
    "MemberCraft",
    "NumberedSource",
    "SubCategoryCount",
    "category_path",
    "contract_text",
    "referenced_claims",
]

CATEGORY_PAGE_SCHEMA_VERSION = 1
CATEGORY_LIST_SCHEMA_VERSION = 1
HYPOTHESIS = "HYPOTHESIS"

ClaimIds = list[uuid.UUID]
Slug = str


def category_path(slug: str) -> str:
    return f"/categories/{slug}"


class CategoryRef(ContractModel):
    slug: str = Field(min_length=1, max_length=SLUG_MAX_CHARS)
    name: str = Field(min_length=1)
    label: str = Field(min_length=1)
    palette: str | None
    path: str
    craft_count: int = Field(ge=0)

    @model_validator(mode="after")
    def _path_names_the_slug(self) -> Self:
        if self.path != category_path(self.slug):
            raise ValueError("path is /categories/<slug>")
        return self


class CategorySearch(ContractModel):
    query: str = Field(min_length=1)
    site: str = Field(min_length=1)


class CategoryCuration(ContractModel):
    version: int = Field(ge=1)
    curated_at: AwareDatetime
    coverage: Literal[*COVERAGE_CLASSES]
    searched: list[CategorySearch]


class CategoryHero(ContractModel):
    media: MediaRef
    caption: str = Field(min_length=1)


class CategorySentence(ContractModel):
    id: str = Field(min_length=1)
    text: str = Field(min_length=1)
    level: EvidenceLevel
    claim_ids: ClaimIds = Field(min_length=1)
    terms: list[TermSpan]
    sub_categories: list[Slug]
    crafts: list[Slug]

    @model_validator(mode="after")
    def _facts_only(self) -> Self:
        if self.level == HYPOTHESIS:
            raise ValueError(f"sentence {self.id} rests on a hypothesis; hypotheses are open questions")
        return self


class CategoryFact(ContractModel):
    label: str = Field(min_length=1)
    value: str = Field(min_length=1)
    claim_ids: ClaimIds = Field(min_length=1)


class CategorySection(ContractModel):
    discipline: Discipline
    title: str = Field(min_length=1)
    sentences: list[CategorySentence] = Field(min_length=1)


class CategoryOverview(ContractModel):
    lede: list[CategorySentence]
    key_facts: list[CategoryFact]
    sections: list[CategorySection]

    def sentences(self) -> list[CategorySentence]:
        return [*self.lede, *(sentence for section in self.sections for sentence in section.sentences)]


class MemberCraft(CraftRef):
    gi_status: Literal[*GI_STATUSES] | None
    catch_all: bool
    curated: bool


class CategorySubCategory(ContractModel):
    slug: str = Field(min_length=1)
    name: str = Field(min_length=1)
    label: str = Field(min_length=1)
    craft_count: int = Field(ge=0)
    crafts: list[MemberCraft]
    sentence: CategorySentence | None
    open_question: str | None

    @model_validator(mode="after")
    def _counts_named_crafts(self) -> Self:
        if self.craft_count != sum(1 for craft in self.crafts if not craft.catch_all):
            raise ValueError(f"sub-category {self.slug} counts its crafts without the catch-all rows")
        if self.sentence is not None and self.slug not in self.sentence.sub_categories:
            raise ValueError(f"the sentence shown for {self.slug} does not cover it")
        return self


class CategoryDiffer(ContractModel):
    about: str = Field(min_length=1)
    claim_ids: ClaimIds = Field(min_length=2)


class CategoryTerm(ContractModel):
    key: str | None
    label: str = Field(min_length=1)
    names: list[str]
    meaning: str = Field(min_length=1)
    language: str | None
    script: str | None
    claim_ids: ClaimIds


class CategoryPicture(ContractModel):
    media: MediaRef
    caption: str = Field(min_length=1)
    claim_ids: ClaimIds = Field(min_length=1)


class CategoryQuestion(ContractModel):
    key: str = Field(min_length=1)
    question: str = Field(min_length=1)
    settled_by: str | None
    claim_ids: ClaimIds
    sub_categories: list[Slug]

    @model_validator(mode="after")
    def _cites_or_names_the_gap(self) -> Self:
        if not self.claim_ids and not self.sub_categories:
            raise ValueError(
                f"question {self.key} cites a claim or names the sub-categories without a source"
            )
        return self


class CategoryClaim(ContractModel):
    id: uuid.UUID
    text: str = Field(min_length=1)
    level: EvidenceLevel
    discipline: Discipline
    sources_differ: bool
    citations: list[Citation] = Field(min_length=1)


class NumberedSource(SourceRef):
    number: int = Field(ge=1)


class CategoryPage(ContractModel):
    schema_version: Literal[1]
    category: CategoryRef
    curated: bool
    curation: CategoryCuration | None
    hero: CategoryHero | None
    overview: CategoryOverview
    sub_categories: list[CategorySubCategory]
    sources_differ: list[CategoryDiffer]
    glossary: list[CategoryTerm]
    pictures: list[CategoryPicture]
    open_questions: list[CategoryQuestion]
    claims: list[CategoryClaim]
    sources: list[NumberedSource]

    @model_validator(mode="after")
    def _everything_resolves(self) -> Self:
        if self.curated != (self.curation is not None):
            raise ValueError("a curated page, and only a curated one, carries its curation header")
        if self.category.craft_count != sum(sub.craft_count for sub in self.sub_categories):
            raise ValueError("the category counts the crafts of its sub-categories")
        _listed_once("sub-categories", [sub.slug for sub in self.sub_categories])
        _claims_resolve(self)
        _sources_resolve(self.claims, self.sources)
        _references_resolve(self)
        return self

    def referenced_claim_ids(self) -> Iterator[uuid.UUID]:
        rows = [*self.sources_differ, *self.glossary, *self.pictures, *self.open_questions]
        return referenced_claims(self.overview, rows)


CitingRow = CategoryDiffer | CategoryTerm | CategoryPicture | CategoryQuestion


class SubCategoryCount(ContractModel):
    slug: str = Field(min_length=1)
    name: str = Field(min_length=1)
    label: str = Field(min_length=1)
    craft_count: int = Field(ge=0)


class CategorySummary(CategoryRef):
    curated: bool
    sub_categories: list[SubCategoryCount]
    hero: CategoryHero | None
    lede: AnswerSentence | None

    @model_validator(mode="after")
    def _counts_add_up(self) -> Self:
        if self.craft_count != sum(sub.craft_count for sub in self.sub_categories):
            raise ValueError(f"{self.slug} counts the crafts of its sub-categories")
        if not self.curated and (self.lede is not None or self.hero is not None):
            raise ValueError(f"{self.slug} is not curated, so it has no lede and no hero")
        return self


class CategoryList(ContractModel):
    schema_version: Literal[1]
    categories: list[CategorySummary]
    sources: list[SourceRef]

    @model_validator(mode="after")
    def _ledes_cite_listed_sources(self) -> Self:
        _listed_once("categories", [category.slug for category in self.categories])
        _listed_once("sources", [source.id for source in self.sources])
        cited = [
            citation.source_id
            for category in self.categories
            if category.lede is not None
            for citation in category.lede.citations
        ]
        if set(cited) != {source.id for source in self.sources}:
            raise ValueError("the list carries exactly the sources its ledes cite")
        return self


def referenced_claims(overview: CategoryOverview, rows: Sequence[CitingRow]) -> Iterator[uuid.UUID]:
    lists = [sentence.claim_ids for sentence in overview.lede]
    lists += [fact.claim_ids for fact in overview.key_facts]
    lists += [s.claim_ids for section in overview.sections for s in section.sentences]
    lists += [row.claim_ids for row in rows]
    for listed in lists:
        yield from listed


def _listed_once(what: str, keys: Sequence[str]) -> None:
    repeated = sorted(key for key, count in Counter(keys).items() if count > 1)
    if repeated:
        raise ValueError(f"{what} are listed once each; repeated: {', '.join(repeated)}")


def _claims_resolve(page: CategoryPage) -> None:
    listed = [claim.id for claim in page.claims]
    _listed_once("claims", [str(claim_id) for claim_id in listed])
    referenced = set(page.referenced_claim_ids())
    unknown = sorted(str(claim_id) for claim_id in referenced - set(listed))
    if unknown:
        raise ValueError(f"the page refers to claims it does not list: {', '.join(unknown)}")
    uncited = sorted(str(claim_id) for claim_id in set(listed) - referenced)
    if uncited:
        raise ValueError(f"the page lists only claims its parts cite: {', '.join(uncited)}")


def _sources_resolve(claims: Sequence[CategoryClaim], sources: Sequence[NumberedSource]) -> None:
    _listed_once("sources", [source.id for source in sources])
    if [source.number for source in sources] != list(range(1, len(sources) + 1)):
        raise ValueError("sources are numbered 1 to N in the order they are listed")
    cited = {citation.source_id for claim in claims for citation in claim.citations}
    if cited != {source.id for source in sources}:
        raise ValueError("the page lists exactly the sources its claims cite")


def _references_resolve(page: CategoryPage) -> None:
    sentences = {sentence.id: sentence for sentence in page.overview.sentences()}
    _listed_once("sentences", [sentence.id for sentence in page.overview.sentences()])
    members = {craft.slug for sub in page.sub_categories for craft in sub.crafts}
    subs = {sub.slug for sub in page.sub_categories}
    for sentence in sentences.values():
        if not set(sentence.crafts) <= members or not set(sentence.sub_categories) <= subs:
            raise ValueError(f"sentence {sentence.id} names a craft or sub-category the page does not list")
    shown = [sub.sentence for sub in page.sub_categories if sub.sentence is not None]
    if any(sentences.get(sentence.id) != sentence for sentence in shown):
        raise ValueError("a sub-category shows a sentence of the overview")
    questions = {question.key for question in page.open_questions}
    if any(sub.open_question not in questions for sub in page.sub_categories if sub.open_question):
        raise ValueError("a sub-category names an open question the page lists")
    if page.hero is not None and page.hero.media not in [picture.media for picture in page.pictures]:
        raise ValueError("the hero is one of the page's pictures")


def contract_text(model: CategoryPage | CategoryList) -> str:
    return json.dumps(model.model_dump(mode="json", by_alias=True), indent=2, ensure_ascii=False) + "\n"
