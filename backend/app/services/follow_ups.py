from __future__ import annotations

import itertools
import re
import uuid
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field

from app.research.explainer import Explainer, ExplainerSection, Understood, explainer_blocks
from app.research.explainer_versions import (
    BuildsOnEvent,
    ExplainerVersionDocument,
    SectionPlace,
    VersionMark,
    block_number,
)
from app.research.sections import DISCIPLINE_TITLES, SectionSpec, section_specs
from app.research.understanding import Understanding

from .section_deepening import Deepening
from .version_merge import merged_version

__all__ = ["AnswerLayout", "FollowUp", "StoredAnswer", "answer_layout", "understood_for"]

SECTION_NUMBER = re.compile(r"^s(?P<number>\d+)$")


@dataclass(frozen=True)
class FollowUp:
    base: ExplainerVersionDocument
    facets: tuple[str, ...] = ()

    @property
    def explainer(self) -> Explainer:
        return self.base.explainer

    @property
    def understood(self) -> Understood:
        return self.base.explainer.understood

    @property
    def craft_slug(self) -> str | None:
        crafts = self.understood.crafts
        return crafts[0].slug if crafts else None

    def event(self) -> BuildsOnEvent:
        return BuildsOnEvent(
            explainer_id=self.base.mark.explainer_id,
            version=self.base.mark.version,
            sections=[
                SectionPlace(id=section.id, order=section.order) for section in self.explainer.sections
            ],
        )


@dataclass(frozen=True)
class StoredAnswer:
    explainer: Explainer | None
    claim_ids: tuple[uuid.UUID, ...]
    version: VersionMark | None = None


@dataclass(frozen=True)
class AnswerLayout:
    specs: tuple[SectionSpec, ...]
    titles: Mapping[str, str] = field(default_factory=dict)
    deepening: Mapping[str, Deepening] = field(default_factory=dict)
    follow_up: FollowUp | None = None

    @property
    def untitled(self) -> list[SectionSpec]:
        return [spec for spec in self.specs if spec.id not in self.titles]

    @property
    def reusable(self) -> list[SectionSpec]:
        return [spec for spec in self.specs if spec.id not in self.deepening]

    def keeps_pieces_of(self, spec: SectionSpec) -> bool:
        return spec.id not in self.deepening

    def understood(self, understanding: Understanding) -> Understood:
        return understood_for(understanding, self.follow_up)

    def stored(self, document: Explainer | None, claim_ids: Iterable[uuid.UUID]) -> StoredAnswer:
        if self.follow_up is None or document is None:
            return StoredAnswer(document, tuple(claim_ids))
        version = merged_version(self.follow_up.base, document)
        cited = [uuid.UUID(c.claim_id) for b in explainer_blocks(version.explainer) for c in b.citations()]
        return StoredAnswer(version.explainer, tuple(dict.fromkeys([*cited, *claim_ids])), version.mark)


def understood_for(understanding: Understanding, follow_up: FollowUp | None) -> Understood:
    return understanding.understood() if follow_up is None else follow_up.understood


def answer_layout(understanding: Understanding, follow_up: FollowUp | None) -> AnswerLayout:
    asked = follow_up.facets if follow_up is not None and follow_up.facets else understanding.disciplines
    specs = section_specs(asked, understanding.depth)
    if follow_up is None:
        return AnswerLayout(specs=tuple(specs))
    return _follow_up_layout(follow_up, [spec.discipline for spec in specs])


def _follow_up_layout(follow_up: FollowUp, disciplines: Sequence[str]) -> AnswerLayout:
    explainer = follow_up.explainer
    by_field = {section.discipline: section for section in explainer.sections}
    shown = frozenset(uuid.UUID(c.claim_id) for b in explainer_blocks(explainer) for c in b.citations())
    numbers = itertools.count(_last_section_number(explainer.sections) + 1)
    orders = itertools.count(len(explainer.sections) + 1)
    specs: list[SectionSpec] = []
    titles: dict[str, str] = {}
    deepening: dict[str, Deepening] = {}
    for discipline in disciplines:
        section = by_field.get(discipline)
        if section is None:
            title = DISCIPLINE_TITLES[discipline]
            specs.append(
                SectionSpec(id=f"s{next(numbers)}", discipline=discipline, title=title, order=next(orders))
            )
            continue
        specs.append(_deepened_spec(section))
        titles[section.id] = section.title
        deepening[section.id] = _deepening(section, shown)
    ordered = tuple(sorted(specs, key=lambda spec: spec.order))
    return AnswerLayout(specs=ordered, titles=titles, deepening=deepening, follow_up=follow_up)


def _deepened_spec(section: ExplainerSection) -> SectionSpec:
    return SectionSpec(
        id=section.id,
        discipline=section.discipline,
        title=section.original or section.title,
        order=section.order,
    )


def _deepening(section: ExplainerSection, shown: frozenset[uuid.UUID]) -> Deepening:
    last = max((block_number(block.id, section.id) for block in section.blocks), default=0)
    return Deepening(
        first_block=last + 1, kinds=frozenset(block.kind for block in section.blocks), claims=shown
    )


def _last_section_number(sections: Sequence[ExplainerSection]) -> int:
    found = (SECTION_NUMBER.match(section.id) for section in sections)
    return max((int(match.group("number")) for match in found if match), default=0)
