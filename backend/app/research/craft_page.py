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
from .craft_page_context import (
    DIFFER_WEIGHTS,
    PICTURE_ROLES,
    SAME_FAMILY_MAX,
    EnvironmentStep,
    LocalName,
    PageDepth,
    PageEvent,
    PageGi,
    PageRelative,
    PageTabs,
)
from .craft_page_process import PageProcess
from .crafts import CraftRef
from .media_refs import MediaRef
from .terms import TermSpan
from .vocabulary import Discipline, EvidenceLevel

__all__ = [
    "CRAFT_PAGE_SCHEMA_VERSION",
    "HERO",
    "PROVENANCES",
    "SECTION_BASES",
    "SUBJECT_KINDS",
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
    "PageQuestion",
    "PageSentence",
    "PageTerm",
    "SearchedFor",
    "SubjectRef",
    "craft_page_text",
    "without_evidence",
]

CRAFT_PAGE_SCHEMA_VERSION = 2
PROVENANCES = ("CURATED", "SEED", "FROM_ANSWERS", "RESEARCHER")
SECTION_BASES = ("CURATED", "STORED_CLAIMS")
SUBJECT_KINDS = ("CRAFT", "STAGE", "MATERIAL", "TOOL", "PLACE", "COMMUNITY", "TERM", "CONCEPT")
HYPOTHESIS = "HYPOTHESIS"
HERO = "HERO"

ClaimIds = list[uuid.UUID]


class PageCraft(CraftRef):
    id: uuid.UUID
    display_name: str = Field(min_length=1)
    local_name: str | None
    local_names: list[LocalName]
    category_name: str | None
    sub_category_name: str | None
    family_label: str | None
    kind_label: str | None
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
    key: str = Field(min_length=1)
    about: str = Field(min_length=1)
    weight: Literal[*DIFFER_WEIGHTS]
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
    place_key: str | None
    claim_ids: ClaimIds = Field(min_length=1)


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
    role: Literal[*PICTURE_ROLES]
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
    schema_version: Literal[2]
    craft: PageCraft
    curated: bool
    curation: CurationHeader | None
    tabs: PageTabs
    depth: PageDepth
    suggested_questions: list[str] = Field(min_length=1)
    overview: PageOverview
    gi_card: PageGi
    events: list[PageEvent]
    environment: list[EnvironmentStep]
    sources_differ: list[DifferRow]
    places: list[PagePlace]
    communities: list[PageCommunity]
    process: PageProcess
    glossary: list[PageTerm]
    pictures: list[PagePicture]
    open_questions: list[PageQuestion]
    same_family: list[PageRelative] = Field(max_length=SAME_FAMILY_MAX)
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
        _parts_agree(self)
        return self

    def referenced_claim_ids(self) -> Iterator[uuid.UUID]:
        sentences = [
            *self.overview.lede,
            *(s for section in self.overview.sections for s in section.sentences),
        ]
        lists = [sentence.claim_ids for sentence in sentences]
        lists += [name.claim_ids for name in self.craft.local_names]
        lists += [fact.claim_ids for fact in self.overview.key_facts]
        lists += [self.gi_card.claim_ids, *(row.claim_ids for row in [*self.events, *self.environment])]
        lists += [row.claim_ids for row in [*self.sources_differ, *self.places, *self.communities]]
        lists += [row.claim_ids for row in [*self.glossary, *self.pictures, *self.open_questions]]
        lists.append(self.process.cited_claim_ids())
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


def _parts_agree(page: CraftPage) -> None:
    if sum(1 for picture in page.pictures if picture.role == HERO) > 1:
        raise ValueError("a page has one hero picture at most")
    keys = [row.key for row in page.sources_differ]
    if len(keys) != len(set(keys)):
        raise ValueError("each row of sources differ has its own key")
    unknown = {key for stage in page.process.stages for key in stage.differ} - set(keys)
    if unknown:
        raise ValueError(
            f"stages point to sources-differ rows the page does not list: {', '.join(sorted(unknown))}"
        )
    if page.tabs.evidence and page.evidence is None:
        raise ValueError("the All evidence tab is offered only with the evidence")
    pointed = {group.place_key for group in page.communities if group.place_key}
    pointed |= {step.place.key for step in page.environment if step.place}
    unlisted = pointed - {place.key for place in page.places}
    if unlisted:
        raise ValueError(f"parts point to places the page does not list: {', '.join(sorted(unlisted))}")
    if page.craft.slug in {relative.craft.slug for relative in page.same_family}:
        raise ValueError("a craft is not its own relative")


def craft_page_text(page: CraftPage) -> str:
    return json.dumps(page.model_dump(mode="json", by_alias=True), indent=2, ensure_ascii=False) + "\n"


def without_evidence(page: CraftPage) -> CraftPage:
    cited = set(page.referenced_claim_ids())
    claims = [claim for claim in page.claims if claim.id in cited]
    shown = {citation.source_id for claim in claims for citation in claim.citations}
    plain = page.model_dump(by_alias=True)
    plain.update(
        tabs=page.tabs.model_copy(update={"evidence": False}).model_dump(by_alias=True),
        evidence=None,
        claims=[claim.model_dump(by_alias=True) for claim in claims],
        sources=[source.model_dump(by_alias=True) for source in page.sources if source.id in shown],
    )
    return CraftPage.model_validate(plain)
