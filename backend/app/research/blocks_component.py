from __future__ import annotations

import re
from collections.abc import Iterable, Iterator, Mapping
from types import MappingProxyType
from typing import Literal, Self

from pydantic import Field, model_validator

from app.models.knowledge_pieces import LABEL_COLUMN_CHARS, LABEL_PATTERN, TITLE_COLUMN_CHARS

from .base import ContractModel
from .blocks import BlockBase
from .crafts import CraftRef
from .vocabulary import PieceKind

__all__ = [
    "ANCHOR_PATTERN",
    "COMPONENT_KIND",
    "COMPONENT_STANDS_FOR",
    "ComponentBlock",
    "ComponentSource",
    "component_href",
    "stood_for",
]

COMPONENT_KIND = "component"
ANCHOR_PATTERN = re.compile(r"#[A-Za-z][A-Za-z0-9_-]*")
COMPONENT_STANDS_FOR: Mapping[str, str] = MappingProxyType(
    {
        "reaction_player": "reaction_player",
        "molecule_3d": "molecule_3d",
        "timeline_map": "timeline_map",
        "map_layer": "map_layer",
        "material_cards": "material_card",
    }
)


class ComponentSource(ContractModel):
    source_id: str = Field(min_length=1)


class ComponentBlock(BlockBase):
    kind: Literal["component"]
    version: Literal[1]
    label: str = Field(max_length=LABEL_COLUMN_CHARS, pattern=LABEL_PATTERN)
    component_kind: PieceKind
    title: str = Field(min_length=1, max_length=TITLE_COLUMN_CHARS)
    craft: CraftRef
    href: str
    sources: list[ComponentSource] = Field(min_length=1)

    @model_validator(mode="after")
    def _links_the_page_it_comes_from(self) -> Self:
        anchor = self.href.removeprefix(self.craft.path)
        if not self.href.startswith(self.craft.path) or (anchor and not ANCHOR_PATTERN.fullmatch(anchor)):
            raise ValueError(f"component {self.id} links its craft's page, at most with an anchor")
        if self.component_kind == COMPONENT_KIND:
            raise ValueError(f"component {self.id} places a registered component, never another placement")
        return self

    def direct_source_ids(self) -> Iterator[str]:
        for source in self.sources:
            yield source.source_id

    def shown_labels(self) -> list[str]:
        return [self.title]


def component_href(craft: CraftRef, anchor: str) -> str:
    return f"{craft.path}{anchor}" if ANCHOR_PATTERN.fullmatch(anchor) else craft.path


def stood_for(blocks: Iterable[BlockBase]) -> frozenset[str]:
    kinds = (block.component_kind for block in blocks if isinstance(block, ComponentBlock))
    return frozenset(COMPONENT_STANDS_FOR[kind] for kind in kinds if kind in COMPONENT_STANDS_FOR)
