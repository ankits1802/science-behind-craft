from __future__ import annotations

import logging
from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from app.core.errors import InvalidInput
from app.geo.datasets import region_dataset
from app.geo.records import DatasetRecord, ValueRecord
from app.geo.region_view import district_value, region_facets
from app.research.blocks_place import DistrictRef
from app.research.citations import SourceRef
from app.research.crafts import CraftRef
from app.research.datasets import BOUNDARY_CAPTION
from app.research.explainer import Block
from app.research.vocabulary import LEVEL_ORDER, PLACE_ROLES
from app.schemas.district_crafts import (
    DISTRICT_CRAFTS_SCHEMA_VERSION,
    LAND_BLOCKS_MAX,
    LAND_FACETS,
    DistrictCraft,
    DistrictCrafts,
    LandStory,
)
from app.schemas.region import DATASET_FACETS, PlaceBasis, RegionValue

__all__ = ["CRAFT_LOCATION_BASIS", "DEFAULT_ROLE", "DistrictLocation", "DistrictRecords", "district_crafts"]

logger = logging.getLogger(__name__)

CRAFT_LOCATION_BASIS = "CRAFT_LOCATION"
DEFAULT_ROLE = "PRACTISED"


@dataclass(frozen=True)
class DistrictLocation:
    id: str
    craft: CraftRef
    role: str | None
    level: str
    source_id: str
    source_title: str


@dataclass(frozen=True)
class DistrictRecords:
    district: DistrictRef
    boundary: DatasetRecord
    locations: tuple[DistrictLocation, ...]
    values: tuple[ValueRecord, ...]
    datasets: Mapping[str, DatasetRecord]
    blocks: tuple[Block, ...]
    sources: Mapping[str, SourceRef]


def district_crafts(records: DistrictRecords) -> DistrictCrafts:
    crafts = _located_crafts(records.locations)
    values = _land_values(records)
    land = _land(records, values)
    codes = sorted({value.dataset_code for facet in (land.facets if land else []) for value in facet.values})
    return DistrictCrafts(
        schema_version=DISTRICT_CRAFTS_SCHEMA_VERSION,
        district=records.district,
        crafts=crafts,
        land=land,
        sources=_cited_sources(crafts, land, records.sources),
        datasets=[
            region_dataset(records.boundary),
            *(region_dataset(records.datasets[code]) for code in codes),
        ],
        boundary_caption=BOUNDARY_CAPTION,
    )


def _located_crafts(locations: Sequence[DistrictLocation]) -> list[DistrictCraft]:
    by_craft: dict[str, list[DistrictLocation]] = defaultdict(list)
    for location in locations:
        by_craft[location.craft.slug].append(location)
    crafts = [_district_craft(found) for found in by_craft.values()]
    return sorted(crafts, key=lambda entry: (entry.craft.name.casefold(), entry.craft.slug))


def _district_craft(locations: Sequence[DistrictLocation]) -> DistrictCraft:
    strongest = min(
        locations, key=lambda location: (LEVEL_ORDER.get(location.level, len(LEVEL_ORDER)), location.id)
    )
    held = {location.role or DEFAULT_ROLE for location in locations}
    return DistrictCraft(
        craft=strongest.craft,
        roles=[role for role in PLACE_ROLES if role in held],
        basis=PlaceBasis(
            kind=CRAFT_LOCATION_BASIS,
            source_id=strongest.source_id,
            label=strongest.source_title,
            level=strongest.level,
        ),
    )


def _land_values(records: DistrictRecords) -> list[RegionValue]:
    shown = []
    for row in records.values:
        dataset = records.datasets.get(row.dataset_code)
        if dataset is None:
            raise InvalidInput(
                f"a stored value cites dataset {row.dataset_code}, which has no EnvDataset row"
            )
        if DATASET_FACETS.get(row.dataset_code) in LAND_FACETS:
            shown.append(district_value(row, dataset))
    return shown


def _land(records: DistrictRecords, values: Sequence[RegionValue]) -> LandStory | None:
    blocks = [block for block in records.blocks if _sources_shown(block, records.sources)][:LAND_BLOCKS_MAX]
    facets = [facet for facet in region_facets(values) if facet.facet in LAND_FACETS]
    if not blocks and not facets:
        return None
    return LandStory(blocks=blocks, facets=facets)


def _sources_shown(block: Block, sources: Mapping[str, SourceRef]) -> bool:
    hidden = [source_id for source_id in block.cited_source_ids() if source_id not in sources]
    if hidden:
        logger.warning("stored block %s cites sources no longer shown: %s", block.id, ", ".join(hidden))
    return not hidden


def _cited_sources(
    crafts: Sequence[DistrictCraft], land: LandStory | None, sources: Mapping[str, SourceRef]
) -> list[SourceRef]:
    ordered = dict.fromkeys(entry.basis.source_id for entry in crafts if entry.basis.source_id)
    for block in land.blocks if land else []:
        ordered.update(dict.fromkeys(block.cited_source_ids()))
    missing = [source_id for source_id in ordered if source_id not in sources]
    if missing:
        raise InvalidInput(f"district sources {', '.join(missing)} were not loaded")
    return [sources[source_id] for source_id in ordered]
