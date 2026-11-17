from __future__ import annotations

import re
import uuid
from collections.abc import Mapping, Sequence
from types import MappingProxyType
from typing import Any, Literal, Self

from pydantic import AwareDatetime, Field, TypeAdapter, model_validator

from app.models.enums import DISCIPLINES

from .base import ContractModel
from .blocks import BlockBase
from .crafts import QUESTION_MAX_CHARS
from .explainer import SECTION_ID_PATTERN, Explainer, ExplainerSection
from .vocabulary import Discipline

__all__ = [
    "EXPLAINER_VERSION_SCHEMA_VERSION",
    "IMAGES_KIND",
    "SECTION_CHANGES",
    "VERSION_EVENTS",
    "BuildsOn",
    "BuildsOnEvent",
    "ExplainerHistory",
    "ExplainerVersionDocument",
    "SectionChange",
    "SectionPlace",
    "VersionMark",
    "block_number",
    "version_problems",
]

EXPLAINER_VERSION_SCHEMA_VERSION = 1
SECTION_CHANGES = ("ADDED", "DEEPENED")
IMAGES_KIND = "images"
BLOCK_NUMBER = re.compile(r"^(?P<section>s\d+)\.b(?P<number>\d+)$")

SectionChangeName = Literal[*SECTION_CHANGES]


class BuildsOn(ContractModel):
    explainer_id: uuid.UUID
    version: int = Field(ge=1)
    facets: list[Discipline] = Field(max_length=len(DISCIPLINES))

    @model_validator(mode="after")
    def _each_facet_once(self) -> Self:
        if len(set(self.facets)) != len(self.facets):
            raise ValueError("a follow-up deepens each facet once")
        return self


class SectionPlace(ContractModel):
    id: str = Field(pattern=SECTION_ID_PATTERN)
    order: int = Field(ge=1)


class BuildsOnEvent(ContractModel):
    explainer_id: uuid.UUID
    version: int = Field(ge=1)
    sections: list[SectionPlace] = Field(min_length=1)

    @model_validator(mode="after")
    def _the_base_sections_in_order(self) -> Self:
        if [place.order for place in self.sections] != list(range(1, len(self.sections) + 1)):
            raise ValueError("a follow-up builds on the explainer's sections, listed by order")
        return self


class SectionChange(ContractModel):
    section_id: str = Field(pattern=SECTION_ID_PATTERN)
    change: SectionChangeName
    block_ids: list[str] = Field(min_length=1)


class VersionMark(ContractModel):
    explainer_id: uuid.UUID
    version: int = Field(ge=1)
    answer_id: uuid.UUID
    based_on: int | None = Field(ge=1)
    question: str = Field(min_length=1, max_length=QUESTION_MAX_CHARS)
    changes: list[SectionChange]
    created_at: AwareDatetime

    @model_validator(mode="after")
    def _the_first_answer_then_follow_ups(self) -> Self:
        first = self.version == 1
        if first and (self.based_on is not None or self.changes or self.answer_id != self.explainer_id):
            raise ValueError("version 1 is the explainer's own answer, based on nothing and changing nothing")
        if not first and (self.based_on != self.version - 1 or not self.changes):
            raise ValueError(f"version {self.version} builds on version {self.version - 1} and changes it")
        sections = [change.section_id for change in self.changes]
        if len(set(sections)) != len(sections):
            raise ValueError(f"version {self.version} names each changed section once")
        return self


class ExplainerHistory(ContractModel):
    schema_version: Literal[1]
    explainer_id: uuid.UUID
    versions: list[VersionMark] = Field(min_length=1)

    @model_validator(mode="after")
    def _every_version_in_order(self) -> Self:
        if [mark.version for mark in self.versions] != list(range(1, len(self.versions) + 1)):
            raise ValueError("a history lists versions 1 to n")
        if any(mark.explainer_id != self.explainer_id for mark in self.versions):
            raise ValueError("a history lists the versions of one explainer")
        return self


class ExplainerVersionDocument(ContractModel):
    schema_version: Literal[1]
    mark: VersionMark
    explainer: Explainer

    @model_validator(mode="after")
    def _the_document_of_its_answer(self) -> Self:
        if self.explainer.answer_id != self.mark.answer_id or self.explainer.question != self.mark.question:
            raise ValueError("a version shows the explainer its own answer stored")
        return self


def version_problems(base: Explainer, latest: Explainer, changes: Sequence[SectionChange]) -> list[str]:
    problems = []
    if _understood(base) != _understood(latest):
        problems.append("a follow-up keeps the explainer's crafts, depth and language")
    sections = {section.id: section for section in latest.sections}
    expected: list[tuple[str, str, list[str]]] = []
    for kept in base.sections:
        section = sections.get(kept.id)
        if section is None:
            problems.append(f"section {kept.id} is kept by every later version")
            continue
        problems += _kept_section_problems(kept, section)
        added = _added_block_ids(kept, section)
        if added:
            expected.append((kept.id, "DEEPENED", added))
    known = {section.id for section in base.sections}
    for section in latest.sections:
        if section.id not in known:
            if section.order <= len(base.sections):
                problems.append(f"section {section.id} is added after the sections it builds on")
            expected.append((section.id, "ADDED", [block.id for block in section.blocks]))
    if sorted(expected) != sorted((c.section_id, c.change, c.block_ids) for c in changes):
        problems.append("the changes name every added section and every block a follow-up added")
    if not expected:
        problems.append("a follow-up adds or deepens at least one section")
    return problems


def _understood(explainer: Explainer) -> tuple[Any, ...]:
    understood = explainer.understood
    return tuple(c.slug for c in understood.crafts), understood.depth, understood.language


def _kept_section_problems(kept: ExplainerSection, section: ExplainerSection) -> list[str]:
    same = (kept.discipline, kept.title, kept.original, kept.order) == (
        section.discipline,
        section.title,
        section.original,
        section.order,
    )
    problems = [] if same else [f"section {kept.id} keeps its field, title and place"]
    shown = {block.id: block for block in section.blocks}
    if any(_dumped(block) != _dumped(shown.get(block.id)) for block in kept.blocks):
        problems.append(f"section {kept.id} keeps every block it showed, unchanged")
    added = _added_block_ids(kept, section)
    pictures = [block.id for block in kept.blocks if block.kind == IMAGES_KIND]
    own = [block.id for block in kept.blocks if block.kind != IMAGES_KIND]
    if [block.id for block in section.blocks] != [*own, *added, *pictures]:
        problems.append(
            f"section {kept.id} keeps its blocks in order, adds after them and shows pictures last"
        )
    last = max((block_number(block.id, kept.id) for block in kept.blocks), default=0)
    if any(block_number(block_id, kept.id) <= last for block_id in added):
        problems.append(f"section {kept.id} numbers added blocks after its own")
    return problems


def _added_block_ids(kept: ExplainerSection, section: ExplainerSection) -> list[str]:
    known = {block.id for block in kept.blocks}
    return [block.id for block in section.blocks if block.id not in known]


def block_number(block_id: str, section_id: str) -> int:
    found = BLOCK_NUMBER.match(block_id)
    return int(found.group("number")) if found and found.group("section") == section_id else 0


def _dumped(block: BlockBase | None) -> dict[str, Any] | None:
    return None if block is None else block.model_dump(mode="json", by_alias=True)


VERSION_EVENTS: Mapping[str, TypeAdapter[Any]] = MappingProxyType(
    {"builds_on": TypeAdapter(BuildsOnEvent), "version": TypeAdapter(VersionMark)}
)
