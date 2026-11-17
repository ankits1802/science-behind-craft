from __future__ import annotations

from typing import Literal, Self

from pydantic import Field, model_validator

from app.research.base import ContractModel
from app.research.blocks_place import DistrictRef
from app.research.citations import SourceRef
from app.research.crafts import CraftRef
from app.research.datasets import BOUNDARY_CAPTION, BOUNDARY_DATASET_CODE, DatasetRef
from app.research.explainer import BUILT_BLOCK_KINDS, Block
from app.research.vocabulary import PlaceRole
from app.schemas.region import PlaceBasis, RegionFacet

__all__ = [
    "DISTRICT_CRAFTS_SCHEMA_VERSION",
    "LAND_BLOCKS_MAX",
    "LAND_FACETS",
    "DistrictCraft",
    "DistrictCrafts",
    "LandStory",
]

DISTRICT_CRAFTS_SCHEMA_VERSION = 1
LAND_BLOCKS_MAX = 4
LAND_FACETS = ("SOIL", "CLIMATE", "WATER", "TERRAIN")
LOCATED = "CRAFT_LOCATION"
DISTRICT_VALUES = "DISTRICT"


class DistrictCraft(ContractModel):
    craft: CraftRef
    roles: list[PlaceRole] = Field(min_length=1)
    basis: PlaceBasis

    @model_validator(mode="after")
    def _placed_by_a_cited_location(self) -> Self:
        if self.basis.kind != LOCATED:
            raise ValueError(f"{self.craft.slug} is placed in a district only by a cited location")
        if len(set(self.roles)) != len(self.roles):
            raise ValueError(f"{self.craft.slug} names each role in the district once")
        return self


class LandStory(ContractModel):
    blocks: list[Block] = Field(max_length=LAND_BLOCKS_MAX)
    facets: list[RegionFacet]

    @model_validator(mode="after")
    def _stored_stories_and_the_district_s_values(self) -> Self:
        if not self.blocks and not self.facets:
            raise ValueError("the land's story shows a stored story or the district's values")
        for block in self.blocks:
            if block.kind not in BUILT_BLOCK_KINDS or block.reuse is None:
                raise ValueError(f"block {block.id} is a built block placed from a stored piece")
        if len({block.id for block in self.blocks}) != len(self.blocks):
            raise ValueError("each land block id is used once")
        values = [value for facet in self.facets for value in facet.values]
        if any(value.aggregation != DISTRICT_VALUES for value in values):
            raise ValueError("the land's values are the district's own")
        facets = [facet.facet for facet in self.facets]
        if len(set(facets)) != len(facets) or not set(facets) <= set(LAND_FACETS):
            raise ValueError(f"the land's values list each of {', '.join(LAND_FACETS)} at most once")
        return self


class DistrictCrafts(ContractModel):
    schema_version: Literal[1]
    district: DistrictRef
    crafts: list[DistrictCraft]
    land: LandStory | None
    sources: list[SourceRef]
    datasets: list[DatasetRef] = Field(min_length=1)
    boundary_caption: str

    @model_validator(mode="after")
    def _crafts_and_land_with_their_citations(self) -> Self:
        if self.boundary_caption != BOUNDARY_CAPTION:
            raise ValueError("a district map carries the boundary caption word for word")
        slugs = [entry.craft.slug for entry in self.crafts]
        names = [entry.craft.name.casefold() for entry in self.crafts]
        if len(set(slugs)) != len(slugs) or names != sorted(names):
            raise ValueError("a district lists each craft once, by name")
        codes = [dataset.code for dataset in self.datasets]
        if codes != [BOUNDARY_DATASET_CODE, *sorted(_value_codes(self.land))]:
            raise ValueError(
                f"a district cites {BOUNDARY_DATASET_CODE}, then each value's dataset once, by code"
            )
        if [source.id for source in self.sources] != _cited_source_ids(self.crafts, self.land):
            raise ValueError("a district lists every cited source once, in order of first citation")
        return self


def _value_codes(land: LandStory | None) -> set[str]:
    if land is None:
        return set()
    return {value.dataset_code for facet in land.facets for value in facet.values}


def _cited_source_ids(crafts: list[DistrictCraft], land: LandStory | None) -> list[str]:
    ordered = dict.fromkeys(entry.basis.source_id for entry in crafts if entry.basis.source_id)
    for block in land.blocks if land else []:
        ordered.update(dict.fromkeys(block.cited_source_ids()))
    return list(ordered)
