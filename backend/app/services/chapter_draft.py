from __future__ import annotations

import uuid
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any, Self

from app.research.craft_chapters import Borrowed, ItemOrigin
from app.research.craft_parts import PagePart, PagePlate
from app.research.explainer import Block

__all__ = ["ChapterDraft", "Drafted"]


@dataclass(frozen=True)
class Drafted:
    block: Block | None = None
    part: PagePart | None = None
    figure: Mapping[str, Any] = field(default_factory=dict)
    borrowed: tuple[Borrowed, ...] = ()
    origin: ItemOrigin | None = None
    piece_id: uuid.UUID | None = None

    @classmethod
    def of_block(cls, block: Block, **extra: Any) -> Self:
        return cls(block=block, **extra)

    @classmethod
    def of_part(cls, part: PagePart, **extra: Any) -> Self:
        return cls(part=part, **extra)

    @property
    def kind(self) -> str:
        if self.block is not None:
            return self.block.kind
        return str(self.part.kind) if self.part is not None else ""


@dataclass(frozen=True)
class ChapterDraft:
    key: str
    opener: PagePlate | None
    items: Sequence[Drafted]
