from __future__ import annotations

import uuid
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any, Protocol

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.research.explainer import Block
from app.research.planning import PlanRequest
from app.research.sections import SectionSpec
from app.research.structured import StructuredModel

from .answer_events import CitedClaims
from .live_sources import LiveSourcesStore

__all__ = ["BlockBuilder", "BuildAsk", "BuilderTools", "Built", "SourceRefs"]

SourceRefs = Mapping[str, Mapping[str, Any]]


@dataclass(frozen=True)
class BuilderTools:
    sessions: async_sessionmaker[AsyncSession]
    live: LiveSourcesStore
    plan_model: StructuredModel
    compose_model: StructuredModel


@dataclass(frozen=True)
class BuildAsk:
    answer_id: uuid.UUID
    section: SectionSpec
    request: PlanRequest
    blocks: tuple[Block, ...]
    cited: CitedClaims


@dataclass(frozen=True)
class Built:
    blocks: tuple[Block, ...] = ()
    sources: SourceRefs = field(default_factory=dict)


class BlockBuilder(Protocol):
    async def build(self, ask: BuildAsk) -> Built: ...
