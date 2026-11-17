from __future__ import annotations

import json
import uuid
from collections import Counter
from collections.abc import Iterator
from typing import Literal, Self

from pydantic import AwareDatetime, Field, model_validator

from app.models.enums import COVERAGE_CLASSES, GI_STATUSES, PLACE_ROLES

from .base import ContractModel
from .citations import Citation, SourceRef
from .crafts import CraftRef
from .media_refs import MediaRef
from .reactions import SPECIES_ROLES
from .terms import TermSpan
from .vocabulary import Discipline, EvidenceLevel, MaterialKind, MaterialRole, ReactionKind, StageType

__all__ = [
    "CRAFT_PAGE_SCHEMA_VERSION",
    "PROVENANCES",
    "SECTION_BASES",
    "SUBJECT_KINDS",
    "TIMING_KINDS",
    "CraftPage",
    "CurationHeader",
    "DifferRow",
    "EvidenceEntry",
    "EvidenceGroup",
    "EvidenceSubject",
    "KeyFact",
    "OverviewSection",
    "PageArea",
    "PageClaim",
    "PageCommunity",
    "PageCraft",
    "PageEvidence",
    "PageOverview",
    "PagePicture",
    "PagePlace",
    "PageProcess",
    "PageQuestion",
    "PageReaction",
    "PageSentence",
    "PageSpecies",
    "PageStage",
    "PageTerm",
    "SearchedFor",
    "StageItem",
    "StageTiming",
    "SubjectRef",
    "craft_page_text",
    "without_evidence",
]

CRAFT_PAGE_SCHEMA_VERSION = 1
PROVENANCES = ("CURATED", "SEED", "FROM_ANSWERS", "RESEARCHER")
SECTION_BASES = ("CURATED", "STORED_CLAIMS")
SUBJECT_KINDS = ("CRAFT", "STAGE", "MATERIAL", "TOOL", "PLACE", "COMMUNITY", "TERM", "CONCEPT")
TIMING_KINDS = ("DURATION", "SEASON")
HYPOTHESIS = "HYPOTHESIS"

ClaimIds = list[uuid.UUID]


class PageCraft(CraftRef):
    id: uuid.UUID
    local_name: str | None
    category_name: str | None
    sub_category_name: str | None
    gi_status: Literal[*GI_STATUSES] | None
    state_of_practice: list[str]
    state_of_origin: list[str]


class SearchedFor(ContractModel):
    query: str = Field(min_length=1)
    site: str = Field(min_length=1)


class CurationHeader(ContractModel):
    version: int = Field(ge=1)
    curated_at: AwareDatetime
    coverage: Literal[*COVERAGE_CLASSES]
    searched: list[SearchedFor]


class SubjectRef(ContractModel):
    id: uuid.UUID | None
    name: str = Field(min_length=1)
    kind: Literal[*SUBJECT_KINDS]


class PageClaim(ContractModel):
    id: uuid.UUID
    text: str = Field(min_length=1)
    level: EvidenceLevel
    discipline: Discipline
    subject: SubjectRef
    provenance: Literal[*PROVENANCES]
    sources_differ: bool
    citations: list[Citation] = Field(min_length=1)


class PageSentence(ContractModel):
    id: str = Field(min_length=1)
    text: str = Field(min_length=1)
    level: EvidenceLevel
    claim_ids: ClaimIds = Field(min_length=1)
    terms: list[TermSpan]

    @model_validator(mode="after")
    def _facts_only(self) -> Self:
        if self.level == HYPOTHESIS:
            raise ValueError(f"sentence {self.id} rests on a hypothesis; hypotheses are open questions")
        return self


class KeyFact(ContractModel):
    label: str = Field(min_length=1)
    value: str = Field(min_length=1)
    claim_ids: ClaimIds = Field(min_length=1)


class OverviewSection(ContractModel):
    discipline: Discipline
    title: str = Field(min_length=1)
    basis: Literal[*SECTION_BASES]
    sentences: list[PageSentence] = Field(min_length=1)


class PageOverview(ContractModel):
    lede: list[PageSentence]
    key_facts: list[KeyFact]
    sections: list[OverviewSection]


class DifferRow(ContractModel):
    about: str = Field(min_length=1)
    claim_ids: ClaimIds = Field(min_length=2)


class PageArea(ContractModel):
    lgd: int | None
    name: str = Field(min_length=1)


class PagePlace(ContractModel):
    key: str
    name: str = Field(min_length=1)
    kind: str = Field(min_length=1)
    role: Literal[*PLACE_ROLES]
    district: PageArea | None
    state: PageArea | None
    country: str = Field(min_length=1)
    wikidata_id: str | None
    claim_ids: ClaimIds = Field(min_length=1)


class PageCommunity(ContractModel):
    key: str
    kind: str = Field(min_length=1)
    name: str = Field(min_length=1)
    local_names: list[str]
    honours: list[str]
    place: str | None
    claim_ids: ClaimIds = Field(min_length=1)


class StageItem(ContractModel):
    id: uuid.UUID
    name: str = Field(min_length=1)
    kind: MaterialKind
    role: MaterialRole
    local_names: list[str]
    claim_ids: ClaimIds = Field(min_length=1)


class StageTiming(ContractModel):
    kind: Literal[*TIMING_KINDS]
    text: str = Field(min_length=1)
    claim_id: uuid.UUID


class PageSpecies(ContractModel):
    role: Literal[*SPECIES_ROLES]
    name: str | None
    formula: str | None
    coefficient: int | None = Field(ge=1)


class PageReaction(ContractModel):
    id: uuid.UUID | None
    kind: ReactionKind
    label: str = Field(min_length=1)
    species: list[PageSpecies] = Field(min_length=2)
    balanced: bool
    equation: str | None
    claim_ids: ClaimIds = Field(min_length=1)

    @model_validator(mode="after")
    def _equation_only_when_balanced(self) -> Self:
        if (self.equation is not None) != self.balanced:
            raise ValueError("a reaction shows an equation only when it balances")
        return self


class PageStage(ContractModel):
    id: uuid.UUID
    order: int | None = Field(ge=1)
    name: str = Field(min_length=1)
    local_name: str | None
    stage_type: StageType
    claim_ids: ClaimIds = Field(min_length=1)
    materials: list[StageItem]
    tools: list[StageItem]
    timing: list[StageTiming]
    reactions: list[PageReaction]


class PageProcess(ContractModel):
    process_id: uuid.UUID | None
    stages: list[PageStage]
    reactions: list[PageReaction]


class PageTerm(ContractModel):
    key: str | None
    label: str = Field(min_length=1)
    names: list[str]
    meaning: str | None
    language: str | None
    script: str | None
    claim_ids: ClaimIds


class PagePicture(ContractModel):
    media: MediaRef
    caption: str = Field(min_length=1)
    stage_id: uuid.UUID | None
    claim_ids: ClaimIds


class PageQuestion(ContractModel):
    key: str | None
    question: str = Field(min_length=1)
    settled_by: str | None
    claim_ids: ClaimIds = Field(min_length=1)


class EvidenceEntry(ContractModel):
    claim_id: uuid.UUID
    folded_ids: ClaimIds


class EvidenceSubject(ContractModel):
    subject: SubjectRef
    entries: list[EvidenceEntry] = Field(min_length=1)


class EvidenceGroup(ContractModel):
    discipline: Discipline
    title: str = Field(min_length=1)
    subjects: list[EvidenceSubject] = Field(min_length=1)


class PageEvidence(ContractModel):
    groups: list[EvidenceGroup]
    hypotheses: list[EvidenceEntry]

    def entries(self) -> Iterator[tuple[EvidenceEntry, bool]]:
        for group in self.groups:
            for subject in group.subjects:
                yield from ((entry, False) for entry in subject.entries)
        yield from ((entry, True) for entry in self.hypotheses)


class CraftPage(ContractModel):
    schema_version: Literal[1]
    craft: PageCraft
    curated: bool
    curation: CurationHeader | None
    overview: PageOverview
    sources_differ: list[DifferRow]
    places: list[PagePlace]
    communities: list[PageCommunity]
    process: PageProcess
    glossary: list[PageTerm]
    pictures: list[PagePicture]
    open_questions: list[PageQuestion]
    evidence: PageEvidence | None
    claims: list[PageClaim]
    sources: list[SourceRef]

    @model_validator(mode="after")
    def _everything_resolves(self) -> Self:
        if self.curated != (self.curation is not None):
            raise ValueError("a curated page, and only a curated one, carries its curation header")
        levels = _listed_once({claim.id: claim.level for claim in self.claims}, [c.id for c in self.claims])
        unknown = sorted(str(claim_id) for claim_id in self.referenced_claim_ids() if claim_id not in levels)
        if unknown:
            raise ValueError(f"the page refers to claims it does not list: {', '.join(unknown)}")
        if self.evidence is None:
            uncited = sorted(str(claim_id) for claim_id in set(levels) - set(self.referenced_claim_ids()))
            if uncited:
                raise ValueError(
                    f"a page without all evidence lists only claims its parts cite: {', '.join(uncited)}"
                )
        else:
            _evidence_covers(self.evidence, levels)
        _sources_resolve(self)
        return self

    def referenced_claim_ids(self) -> Iterator[uuid.UUID]:
        sentences = [
            *self.overview.lede,
            *(s for section in self.overview.sections for s in section.sentences),
        ]
        lists = [sentence.claim_ids for sentence in sentences]
        lists += [fact.claim_ids for fact in self.overview.key_facts]
        lists += [row.claim_ids for row in [*self.sources_differ, *self.places, *self.communities]]
        lists += [row.claim_ids for row in [*self.glossary, *self.pictures, *self.open_questions]]
        lists += [reaction.claim_ids for reaction in self.process.reactions]
        for stage in self.process.stages:
            lists += [stage.claim_ids, *(item.claim_ids for item in [*stage.materials, *stage.tools])]
            lists += [[timing.claim_id] for timing in stage.timing]
            lists += [reaction.claim_ids for reaction in stage.reactions]
        for listed in lists:
            yield from listed


def _listed_once(levels: dict[uuid.UUID, str], ids: list[uuid.UUID]) -> dict[uuid.UUID, str]:
    repeated = sorted(str(claim_id) for claim_id, count in Counter(ids).items() if count > 1)
    if repeated:
        raise ValueError(f"claims are listed once each; repeated: {', '.join(repeated)}")
    return levels


def _evidence_covers(evidence: PageEvidence, levels: dict[uuid.UUID, str]) -> None:
    seen: list[uuid.UUID] = []
    for entry, hypotheses in evidence.entries():
        for claim_id in [entry.claim_id, *entry.folded_ids]:
            if claim_id not in levels:
                raise ValueError(f"evidence lists claim {claim_id}, which the page does not list")
            if (levels[claim_id] == HYPOTHESIS) != hypotheses:
                raise ValueError(f"claim {claim_id} is filed with the wrong kind: hypotheses stand apart")
            seen.append(claim_id)
    if sorted(map(str, seen)) != sorted(map(str, levels)):
        raise ValueError("all evidence lists every claim of the page exactly once")


def _sources_resolve(page: CraftPage) -> None:
    listed = [source.id for source in page.sources]
    if len(listed) != len(set(listed)):
        raise ValueError("sources are listed once each")
    cited = {citation.source_id for claim in page.claims for citation in claim.citations}
    if cited - set(listed):
        raise ValueError(f"cited sources missing from the page: {', '.join(sorted(cited - set(listed)))}")


def craft_page_text(page: CraftPage) -> str:
    return json.dumps(page.model_dump(mode="json", by_alias=True), indent=2, ensure_ascii=False) + "\n"


def without_evidence(page: CraftPage) -> CraftPage:
    cited = set(page.referenced_claim_ids())
    claims = [claim for claim in page.claims if claim.id in cited]
    sources = {source.id: source for source in page.sources}
    shown = dict.fromkeys(citation.source_id for claim in claims for citation in claim.citations)
    plain = page.model_dump(by_alias=True)
    plain.update(
        evidence=None,
        claims=[claim.model_dump(by_alias=True) for claim in claims],
        sources=[sources[source_id].model_dump(by_alias=True) for source_id in shown if source_id in sources],
    )
    return CraftPage.model_validate(plain)
