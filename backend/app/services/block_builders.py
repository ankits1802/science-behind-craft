from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable, Collection, Mapping, Sequence
from dataclasses import KW_ONLY, dataclass, field
from typing import Any, Self

from app.core.errors import InvalidInput
from app.models.enums import DISCIPLINES
from app.research.expert_panel import PANEL_FIELDS
from app.research.explainer import BLOCK_PHASES, BUILT_BLOCK_KINDS, Block
from app.research.piece_reuse import REGION_STORY_FACETS, SIMULATION_FACETS
from app.research.sections import block_id

from .builder_interface import BlockBuilder, BuildAsk, BuilderTools, Built, SourceRefs
from .climate_risk import CLIMATE_RISK_WAIT_SECONDS, ClimateRiskBuilder
from .expert_views import EXPERT_VIEW_WAIT_SECONDS, ExpertPanelBuilder
from .journey_builders import (
    TIMELINE_MAP_WAIT_SECONDS,
    ZOOM_STORY_WAIT_SECONDS,
    TimelineMapBuilder,
    ZoomStoryBuilder,
)
from .learning_builders import COMPARE_FIELDS, CONCEPT_GRAPH_FIELDS, CompareBuilder, ConceptGraphBuilder
from .market_builder import MARKET_FIELDS, MarketGiBuilder
from .matter_builders import (
    MATERIAL_CARD_WAIT_SECONDS,
    MaterialCardBuilder,
    MoleculeBuilder,
    ReactionPlayerBuilder,
)
from .measure_builder import MEASURE_FIELDS, MeasureBuilder
from .place_builders import REGION_STORY_WAIT_SECONDS, MapLayerBuilder, RegionStoryBuilder
from .season_supply_builders import SUPPLY_MAP_WAIT_SECONDS, SeasonsBuilder, SupplyMapBuilder
from .simulation_builder import SIMULATION_WAIT_SECONDS, SimulationBuilder
from .what_if_builder import WHAT_IF_FIELDS, WHAT_IF_WAIT_SECONDS, WhatIfBuilder

__all__ = [
    "BLOCK_BUILDERS",
    "BUILDER_WAIT_MAX_SECONDS",
    "BUILDER_WAIT_SECONDS",
    "AddedBlocks",
    "BlockBuilders",
    "BuilderEntry",
    "SectionBuilds",
    "built_by_registry",
]

logger = logging.getLogger(__name__)

BUILDER_WAIT_SECONDS = 8.0
BUILDER_WAIT_MAX_SECONDS = 60.0
PHASE_A = "A"


@dataclass(frozen=True)
class BuilderEntry:
    kind: str
    disciplines: frozenset[str]
    make: Callable[[BuilderTools], BlockBuilder]
    wait_seconds: float = BUILDER_WAIT_SECONDS
    _: KW_ONLY
    rebuilt_on_reuse: bool = False
    places_pieces: bool = False

    def __post_init__(self) -> None:
        if BLOCK_PHASES.get(self.kind, PHASE_A) == PHASE_A:
            raise InvalidInput(f"a builder adds a later phase's block kind, not {self.kind!r}")
        if not self.disciplines or not self.disciplines <= set(DISCIPLINES):
            raise InvalidInput(f"the {self.kind} builder names the fields it adds blocks to")
        if not 0 < self.wait_seconds <= BUILDER_WAIT_MAX_SECONDS:
            raise InvalidInput(f"the {self.kind} builder waits at most {BUILDER_WAIT_MAX_SECONDS} s")


BLOCK_BUILDERS: tuple[BuilderEntry, ...] = (
    BuilderEntry("region_story", REGION_STORY_FACETS, RegionStoryBuilder, REGION_STORY_WAIT_SECONDS),
    BuilderEntry("map_layer", frozenset({"GEOLOGY", "CLIMATE"}), MapLayerBuilder, rebuilt_on_reuse=True),
    BuilderEntry("seasons", frozenset({"CLIMATE"}), SeasonsBuilder),
    BuilderEntry(
        "climate_risk",
        frozenset({"CLIMATE"}),
        ClimateRiskBuilder,
        CLIMATE_RISK_WAIT_SECONDS,
        rebuilt_on_reuse=True,
    ),
    BuilderEntry("supply_map", frozenset({"MATERIALS"}), SupplyMapBuilder, SUPPLY_MAP_WAIT_SECONDS),
    BuilderEntry("measure", MEASURE_FIELDS, MeasureBuilder),
    BuilderEntry("market_gi", MARKET_FIELDS, MarketGiBuilder, rebuilt_on_reuse=True),
    BuilderEntry("reaction_player", frozenset({"CHEMISTRY"}), ReactionPlayerBuilder),
    BuilderEntry(
        "material_card",
        frozenset({"CHEMISTRY", "MATERIALS"}),
        MaterialCardBuilder,
        MATERIAL_CARD_WAIT_SECONDS,
    ),
    BuilderEntry(
        "molecule_3d", frozenset({"CHEMISTRY", "MATERIALS"}), MoleculeBuilder, rebuilt_on_reuse=True
    ),
    BuilderEntry("expert_view", PANEL_FIELDS, ExpertPanelBuilder, EXPERT_VIEW_WAIT_SECONDS),
    BuilderEntry("what_if", WHAT_IF_FIELDS, WhatIfBuilder, WHAT_IF_WAIT_SECONDS),
    BuilderEntry(
        "simulation", SIMULATION_FACETS, SimulationBuilder, SIMULATION_WAIT_SECONDS, places_pieces=True
    ),
    BuilderEntry("zoom_story", frozenset({"MATERIALS"}), ZoomStoryBuilder, ZOOM_STORY_WAIT_SECONDS),
    BuilderEntry("timeline_map", frozenset({"HISTORY"}), TimelineMapBuilder, TIMELINE_MAP_WAIT_SECONDS),
    BuilderEntry("compare", COMPARE_FIELDS, CompareBuilder, rebuilt_on_reuse=True),
    BuilderEntry("concept_graph", CONCEPT_GRAPH_FIELDS, ConceptGraphBuilder, rebuilt_on_reuse=True),
)


@dataclass(frozen=True)
class AddedBlocks:
    blocks: tuple[Block, ...] = ()
    sources: SourceRefs = field(default_factory=dict)


class BlockBuilders:
    def __init__(self, builders: Sequence[tuple[BuilderEntry, BlockBuilder]] = ()) -> None:
        self._builders = tuple(builders)

    @classmethod
    def from_registry(cls, tools: BuilderTools, entries: Sequence[BuilderEntry] = BLOCK_BUILDERS) -> Self:
        return cls([(entry, entry.make(tools)) for entry in entries if entry.kind in BUILT_BLOCK_KINDS])

    def for_section(self, discipline: str) -> tuple[tuple[BuilderEntry, BlockBuilder], ...]:
        return tuple(pair for pair in self._builders if discipline in pair[0].disciplines)

    def for_reuse(self) -> BlockBuilders:
        return BlockBuilders([pair for pair in self._builders if pair[0].rebuilt_on_reuse])

    def without(self, kinds: Collection[str]) -> BlockBuilders:
        return BlockBuilders([pair for pair in self._builders if pair[0].kind not in kinds])

    def building(self) -> SectionBuilds:
        return SectionBuilds(self)

    async def added(self, ask: BuildAsk) -> AddedBlocks:
        chosen = self.for_section(ask.section.discipline)
        if not chosen:
            return AddedBlocks()
        results = await asyncio.gather(*(_bounded(entry, builder, ask) for entry, builder in chosen))
        blocks: list[Block] = []
        sources: dict[str, Mapping[str, Any]] = {}
        for (entry, _), built in zip(chosen, results, strict=True):
            known = {**ask.cited.sources, **built.sources}
            for block in built.blocks:
                refusal = _refusal(entry, block, known)
                if refusal is not None:
                    logger.warning(
                        "a %s block of section %s is dropped: %s", entry.kind, ask.section.id, refusal
                    )
                    continue
                blocks.append(block)
                sources.update({sid: known[sid] for sid in block.cited_source_ids()})
        return AddedBlocks(tuple(blocks), sources)


class SectionBuilds:
    def __init__(self, builders: BlockBuilders) -> None:
        self._builders = builders
        self._running: asyncio.Task[AddedBlocks] | None = None

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, *exc_info: object) -> None:
        running, self._running = self._running, None
        if running is not None:
            running.cancel()
            await asyncio.gather(running, return_exceptions=True)

    def start(self, ask: BuildAsk) -> None:
        if self._running is None and ask.blocks and self._builders.for_section(ask.section.discipline):
            self._running = asyncio.create_task(self._builders.added(ask))

    async def added(self, section_id: str, *, first_ordinal: int) -> AddedBlocks:
        running, self._running = self._running, None
        if running is None:
            return AddedBlocks()
        found = await running
        placed = tuple(
            block.model_copy(update={"id": block_id(section_id, first_ordinal + n)})
            for n, block in enumerate(found.blocks)
        )
        return AddedBlocks(placed, found.sources)


def built_by_registry(entries: Sequence[BuilderEntry] = BLOCK_BUILDERS) -> frozenset[str]:
    return frozenset(entry.kind for entry in entries)


async def _bounded(entry: BuilderEntry, builder: BlockBuilder, ask: BuildAsk) -> Built:
    try:
        async with asyncio.timeout(entry.wait_seconds):
            return await builder.build(ask)
    except TimeoutError:
        logger.warning(
            "the %s builder for section %s took over %s s; it adds nothing",
            entry.kind,
            ask.section.id,
            entry.wait_seconds,
        )
    except Exception:
        logger.warning(
            "the %s builder for section %s failed; it adds nothing", entry.kind, ask.section.id, exc_info=True
        )
    return Built()


def _refusal(entry: BuilderEntry, block: Block, known: SourceRefs) -> str | None:
    if block.kind != entry.kind:
        return f"the {entry.kind} builder made a {block.kind} block"
    if block.kind not in BUILT_BLOCK_KINDS:
        return f"{block.kind} is not built yet"
    if block.reuse is not None and not entry.places_pieces:
        return "a built block carries no reuse mark"
    unknown = [sid for sid in block.cited_source_ids() if sid not in known]
    if unknown:
        return f"it cites sources the builder did not return: {', '.join(unknown)}"
    return None
