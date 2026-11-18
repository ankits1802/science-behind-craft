from __future__ import annotations

import uuid
from typing import Literal, Self

from pydantic import Field, model_validator

from app.models.enums import COVERAGE_CLASSES, ENVIRONMENT_FACTORS, GI_STATUSES

from .base import ContractModel, PartialDate
from .citations import Citation, SourceRef
from .crafts import CraftRef
from .media_refs import MediaRef

__all__ = [
    "DEPTH_BASES",
    "DIFFER_WEIGHTS",
    "EVENT_KINDS",
    "PICTURE_ROLES",
    "SAME_FAMILY_MAX",
    "EnvironmentStep",
    "HeroImage",
    "LocalName",
    "PageDepth",
    "PageEvent",
    "PageGi",
    "PageRelative",
    "PageTabs",
    "RelativeLede",
    "StepPlace",
]

DEPTH_BASES = ("CURATED", "STORED_CLAIMS", "REGISTER")
EVENT_KINDS = ("STATED", "GI_FILED", "GI_REGISTERED", "PRICE", "WORKFORCE")
PICTURE_ROLES = ("HERO", "OVERVIEW", "STAGE")
DIFFER_WEIGHTS = (1, 2, 3)
SAME_FAMILY_MAX = 6
INLINE = "INLINE"
CURATED = "CURATED"

ClaimIds = list[uuid.UUID]
Coverage = Literal[*COVERAGE_CLASSES]
DepthBasis = Literal[*DEPTH_BASES]
GiStatusName = Literal[*GI_STATUSES]


class LocalName(ContractModel):
    name: str = Field(min_length=1)
    language: str | None
    script: str | None
    claim_ids: ClaimIds = Field(min_length=1)


class PageTabs(ContractModel):
    process: bool
    region: bool
    shared_science: bool
    sources: bool
    evidence: bool


class PageDepth(ContractModel):
    basis: DepthBasis
    coverage: Coverage | None
    claims: int = Field(ge=0)
    sources: int = Field(ge=0)
    stages: int = Field(ge=0)
    pictures: int = Field(ge=0)

    @model_validator(mode="after")
    def _coverage_only_when_curated(self) -> Self:
        _check_coverage(self.basis, self.coverage)
        if self.basis == "REGISTER" and self.claims:
            raise ValueError("a register-only page has no claims")
        return self


class PageGi(ContractModel):
    status: GiStatusName | None
    application_number: str | None = Field(min_length=1, max_length=40)
    certificate_number: str | None = Field(min_length=1, max_length=40)
    filed_on: PartialDate | None
    registered_on: PartialDate | None
    journal_issue: str | None = Field(min_length=1, max_length=100)
    proprietors: list[str]
    authorised_user_count: int | None = Field(ge=0)
    claim_ids: ClaimIds

    @model_validator(mode="after")
    def _a_record_rests_on_claims(self) -> Self:
        recorded = [
            self.application_number,
            self.certificate_number,
            self.filed_on,
            self.registered_on,
            self.journal_issue,
            self.authorised_user_count,
            *self.proprietors,
        ]
        if any(value is not None for value in recorded) and not self.claim_ids:
            raise ValueError("a GI record is shown only with the claims that state it")
        return self


class PageEvent(ContractModel):
    kind: Literal[*EVENT_KINDS]
    start: int
    end: int
    date: PartialDate | None
    place: str | None
    claim_ids: ClaimIds = Field(min_length=1)

    @model_validator(mode="after")
    def _a_span_in_order(self) -> Self:
        if self.start > self.end:
            raise ValueError(f"an event runs forward in time, not {self.start} to {self.end}")
        if self.date is not None and not self.start <= int(self.date[:4]) <= self.end:
            raise ValueError(f"event date {self.date} lies outside {self.start} to {self.end}")
        return self


class StepPlace(ContractModel):
    key: str = Field(min_length=1)
    name: str = Field(min_length=1)


class EnvironmentStep(ContractModel):
    factor: Literal[*ENVIRONMENT_FACTORS]
    place: StepPlace | None
    claim_ids: ClaimIds = Field(min_length=1)


class HeroImage(ContractModel):
    media: MediaRef
    caption: str = Field(min_length=1)

    @model_validator(mode="after")
    def _shown_inline(self) -> Self:
        if self.media.display != INLINE:
            raise ValueError(f"media {self.media.id} leads a page only when it is shown inline")
        return self


class RelativeLede(ContractModel):
    text: str = Field(min_length=1)
    citations: list[Citation] = Field(min_length=1)
    sources: list[SourceRef]

    @model_validator(mode="after")
    def _every_citation_resolves(self) -> Self:
        cited = list(dict.fromkeys(citation.source_id for citation in self.citations))
        if [source.id for source in self.sources] != cited:
            raise ValueError("a family lede lists each source it cites once, in order of first citation")
        return self


class PageRelative(ContractModel):
    craft: CraftRef
    display_name: str = Field(min_length=1)
    gi_status: GiStatusName | None
    state_of_practice: list[str]
    basis: DepthBasis
    coverage: Coverage | None
    claims: int = Field(ge=0)
    hero: HeroImage | None
    lede: RelativeLede | None

    @model_validator(mode="after")
    def _depth_agrees(self) -> Self:
        _check_coverage(self.basis, self.coverage)
        return self


def _check_coverage(basis: str, coverage: str | None) -> None:
    if (basis == CURATED) != (coverage is not None):
        raise ValueError("a curated page, and only a curated one, names its coverage class")
