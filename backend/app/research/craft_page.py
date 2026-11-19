from __future__ import annotations

import json
import uuid
from collections.abc import Iterator
from typing import Literal, Self

from pydantic import AwareDatetime, Field, model_validator

from app.models.enums import COVERAGE_CLASSES, GI_STATUSES, PLACE_ROLES

from .base import ContractModel
from .blocks import ExplainerSentence
from .citations import Citation
from .craft_chapters import Chapter
from .craft_contributed import ContributedPlate
from .craft_masthead import CiteThis, Masthead, PageSource
from .craft_page_checks import chapters_agree, cited_ids, evidence_covers, listed_once, v2_parts_agree
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
from .craft_parts import ContributedPart
from .crafts import CraftRef
from .field_voices import FieldVoicesTotals, PageFieldPhoto, PageVoice
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
]

CRAFT_PAGE_SCHEMA_VERSION = 3
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
    schema_version: Literal[3]
    craft: PageCraft
    curated: bool
    curation: CurationHeader | None
    depth: PageDepth
    suggested_questions: list[str] = Field(min_length=1)
    masthead: Masthead
    lede: list[ExplainerSentence]
    chapters: list[Chapter] = Field(min_length=1)
    cite: CiteThis | None
    glossary: list[PageTerm]
    evidence: PageEvidence
    claims: list[PageClaim]
    sources: list[PageSource]
    field_voices_total: FieldVoicesTotals
    tabs: PageTabs
    overview: PageOverview
    gi_card: PageGi
    events: list[PageEvent]
    environment: list[EnvironmentStep]
    sources_differ: list[DifferRow]
    places: list[PagePlace]
    communities: list[PageCommunity]
    process: PageProcess
    pictures: list[PagePicture]
    open_questions: list[PageQuestion]
    same_family: list[PageRelative] = Field(max_length=SAME_FAMILY_MAX)
    voices: list[PageVoice]
    field_photos: list[PageFieldPhoto]

    @model_validator(mode="after")
    def _everything_resolves(self) -> Self:
        if self.curated != (self.curation is not None):
            raise ValueError("a curated page, and only a curated one, carries its curation header")
        levels = listed_once({claim.id: claim.level for claim in self.claims}, [c.id for c in self.claims])
        unknown = sorted(str(claim_id) for claim_id in self.referenced_claim_ids() if claim_id not in levels)
        if unknown:
            raise ValueError(f"the page refers to claims it does not list: {', '.join(unknown)}")
        evidence_covers(self.evidence, levels)
        self._sources_resolve()
        chapters_agree(self)
        v2_parts_agree(self)
        return self

    def referenced_claim_ids(self) -> Iterator[uuid.UUID]:
        yield from self.flat_claim_ids()
        yield from cited_ids(self.shown_citations(kin=False))

    def flat_claim_ids(self) -> Iterator[uuid.UUID]:
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

    def shown_citations(self, *, kin: bool) -> Iterator[Citation]:
        masthead = self.masthead
        if masthead.gi is not None:
            yield from masthead.gi.citations
        plates = [masthead.picture] if masthead.picture else []
        plates += [chapter.opener for chapter in self.chapters if chapter.opener]
        for sentence in [*self.lede, *(s for plate in plates for s in plate.sentences)]:
            yield from sentence.citations
        for chapter in self.chapters:
            for item in chapter.items:
                if kin or not item.kin:
                    yield from item.citations()

    def contributed_plates(self) -> Iterator[ContributedPlate]:
        for chapter in self.chapters:
            for item in chapter.items:
                if isinstance(item.part, ContributedPart):
                    yield from item.part.pictures

    def _sources_resolve(self) -> None:
        listed = [source.id for source in self.sources]
        if len(listed) != len(set(listed)):
            raise ValueError("sources are listed once each")
        cited = {citation.source_id for claim in self.claims for citation in claim.citations}
        cited |= {voice.source_id for voice in self.voices}
        cited |= {citation.source_id for citation in self.shown_citations(kin=True)}
        cited |= {
            sid for chapter in self.chapters for item in chapter.items for sid in item.cited_source_ids()
        }
        if cited - set(listed):
            raise ValueError(f"cited sources missing from the page: {', '.join(sorted(cited - set(listed)))}")


def craft_page_text(page: CraftPage) -> str:
    return json.dumps(page.model_dump(mode="json", by_alias=True), indent=2, ensure_ascii=False) + "\n"
