from __future__ import annotations

import uuid
from collections.abc import Iterator
from typing import Literal, Self

from pydantic import Field, model_validator

from .base import ContractModel
from .blocks import BlockBase, ExplainerSentence
from .citations import AnswerSentence
from .terms import WIKIDATA_ID_PATTERN

__all__ = [
    "DATASET_CODE_PATTERN",
    "LAYER_KEY_PATTERN",
    "MONTHS",
    "DistrictRef",
    "MapLayerBlock",
    "MonthlyRain",
    "RegionStoryBlock",
    "RiverPath",
    "SeasonRow",
    "SeasonsBlock",
    "StoryStep",
    "SupplyLink",
    "SupplyMapBlock",
    "TimelineMapBlock",
    "TimelinePoint",
    "TimelineRoute",
]

DATASET_CODE_PATTERN = r"^[A-Z0-9]+(?:_[A-Z0-9]+)*$"
LAYER_KEY_PATTERN = r"^[a-z0-9]+(?:-[a-z0-9]+)*$"
MONTHS = 12


class DistrictRef(ContractModel):
    district_lgd: int = Field(ge=1)
    name: str = Field(min_length=1, max_length=200)
    state_name: str = Field(min_length=1, max_length=200)


class RiverPath(ContractModel):
    name: str | None = Field(max_length=200)
    dataset_code: str = Field(pattern=DATASET_CODE_PATTERN, max_length=80)
    reach_ids: list[int] = Field(min_length=1)

    @model_validator(mode="after")
    def _reaches_once_each(self) -> Self:
        if len(set(self.reach_ids)) != len(self.reach_ids) or any(r < 1 for r in self.reach_ids):
            raise ValueError("a river path lists each reach id once, source to mouth")
        return self


class StoryStep(ContractModel):
    district_lgd: int | None = Field(ge=1)
    sentence: ExplainerSentence


class RegionStoryBlock(BlockBase):
    kind: Literal["region_story"]
    version: Literal[1]
    river: RiverPath | None
    districts: list[DistrictRef]
    steps: list[StoryStep] = Field(min_length=1)
    layers: list[str]
    boundary_caption: str = Field(min_length=1)

    @model_validator(mode="after")
    def _steps_stay_in_the_story(self) -> Self:
        reached = {district.district_lgd for district in self.districts}
        if any(step.district_lgd is not None and step.district_lgd not in reached for step in self.steps):
            raise ValueError(f"region story {self.id} narrates only districts it lists")
        return self

    def cited_sentences(self) -> Iterator[AnswerSentence]:
        for step in self.steps:
            yield step.sentence


class MapLayerBlock(BlockBase):
    kind: Literal["map_layer"]
    version: Literal[1]
    layer: str = Field(pattern=LAYER_KEY_PATTERN, max_length=80)
    layer_version: str = Field(min_length=1, max_length=80)
    basis: str = Field(min_length=1, max_length=300)
    dataset_codes: list[str] = Field(min_length=1)
    highlighted: list[int]
    boundary_caption: str = Field(min_length=1)

    def cites_datasets(self) -> bool:
        return bool(self.dataset_codes)


class SeasonRow(ContractModel):
    stage_id: uuid.UUID | None
    label: str = Field(min_length=1, max_length=120)
    months: list[int] = Field(min_length=1, max_length=MONTHS)
    sentence: ExplainerSentence

    @model_validator(mode="after")
    def _calendar_months(self) -> Self:
        if self.months != sorted(set(self.months)) or not all(1 <= m <= MONTHS for m in self.months):
            raise ValueError(f"season row {self.label!r} lists months 1-12 once each, in order")
        return self


class MonthlyRain(ContractModel):
    district_lgd: int = Field(ge=1)
    dataset_code: str = Field(pattern=DATASET_CODE_PATTERN, max_length=80)
    period: str = Field(min_length=1)
    millimetres: list[float] = Field(min_length=MONTHS, max_length=MONTHS)


class SeasonsBlock(BlockBase):
    kind: Literal["seasons"]
    version: Literal[1]
    rows: list[SeasonRow] = Field(min_length=1)
    rainfall: MonthlyRain | None

    def cited_sentences(self) -> Iterator[AnswerSentence]:
        for row in self.rows:
            yield row.sentence


class SupplyLink(ContractModel):
    material: str = Field(min_length=1, max_length=300)
    material_id: uuid.UUID | None
    origin: str = Field(min_length=1, max_length=300)
    wikidata_id: str | None = Field(pattern=WIKIDATA_ID_PATTERN)
    latitude: float | None = Field(ge=-90, le=90)
    longitude: float | None = Field(ge=-180, le=180)
    sentence: ExplainerSentence

    @model_validator(mode="after")
    def _coordinates_from_wikidata(self) -> Self:
        placed = self.latitude is not None or self.longitude is not None
        if placed and (self.latitude is None or self.longitude is None or self.wikidata_id is None):
            raise ValueError(f"supply origin {self.origin!r} is placed only with Wikidata coordinates")
        return self


class SupplyMapBlock(BlockBase):
    kind: Literal["supply_map"]
    version: Literal[1]
    links: list[SupplyLink] = Field(min_length=1)

    def cited_sentences(self) -> Iterator[AnswerSentence]:
        for link in self.links:
            yield link.sentence


class TimelinePoint(ContractModel):
    label: str = Field(min_length=1, max_length=200)
    year_from: int
    year_to: int
    wikidata_id: str = Field(pattern=WIKIDATA_ID_PATTERN)
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    sentence: ExplainerSentence

    @model_validator(mode="after")
    def _years_in_order(self) -> Self:
        if self.year_from > self.year_to:
            raise ValueError(f"timeline point {self.label!r} starts before it ends")
        return self


class TimelineRoute(ContractModel):
    start: int = Field(ge=0)
    end: int = Field(ge=0)
    sentence: ExplainerSentence


class TimelineMapBlock(BlockBase):
    kind: Literal["timeline_map"]
    version: Literal[1]
    points: list[TimelinePoint] = Field(min_length=1)
    routes: list[TimelineRoute]

    @model_validator(mode="after")
    def _routes_join_listed_points(self) -> Self:
        last = len(self.points) - 1
        if any(r.start > last or r.end > last or r.start == r.end for r in self.routes):
            raise ValueError(f"timeline {self.id} joins two different listed points per route")
        return self

    def cited_sentences(self) -> Iterator[AnswerSentence]:
        yield from (point.sentence for point in self.points)
        yield from (route.sentence for route in self.routes)
