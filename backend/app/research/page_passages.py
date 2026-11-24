from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any

from .monograph_page import MonographContent
from .spec_texts import SPEC_TEXT_TAG, spec_texts
from .translation_passages import (
    UNIT_KEY_MAX_CHARS,
    PassageLeaf,
    TaskPassage,
    is_translatable,
    passage_leaves,
    task_passage,
    unit_hash,
)

__all__ = ["NO_SPECS", "PagePassage", "page_passages"]

NO_SPECS: Mapping[str, Mapping[str, Any]] = MappingProxyType({})


@dataclass(frozen=True)
class PagePassage:
    key: str
    nodes: list[Any]
    claim_ids: list[str]
    chapter: str
    tag: str

    @property
    def source_hash(self) -> str:
        return unit_hash(self.nodes, self.claim_ids)

    def leaves(self) -> list[PassageLeaf]:
        return passage_leaves(self.nodes)

    def task(self) -> TaskPassage:
        return task_passage(self.key, self.nodes, self.claim_ids)


def page_passages(
    content: MonographContent, specs: Mapping[str, Mapping[str, Any]]
) -> dict[str, PagePassage]:
    passages = {
        key: PagePassage(key, unit.nodes, unit.claim_ids, unit.chapter, unit.tag)
        for key, unit in content.units.items()
        if is_translatable(key, unit.nodes)
    }
    for component in content.components:
        spec = specs.get(component.label)
        if spec is None:
            continue
        for text in spec_texts(component.label, component.kind, spec):
            if len(text.key) <= UNIT_KEY_MAX_CHARS and is_translatable(text.key, text.nodes):
                passages.setdefault(
                    text.key, PagePassage(text.key, text.nodes, [], component.chapter, SPEC_TEXT_TAG)
                )
    return passages
