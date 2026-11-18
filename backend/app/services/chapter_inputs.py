from __future__ import annotations

import json
import uuid
from dataclasses import replace
from pathlib import Path
from typing import Literal

from pydantic import Field

from app.geo.climate import ClimateTrends
from app.geo.rainfall import DistrictRainfall
from app.research.base import ContractModel
from app.research.blocks_climate import ClimateSeries, ClimateTrend
from app.research.blocks_place import DistrictRef, MonthlyRain
from app.research.blocks_play import SimulationBlock
from app.research.citations import SourceRef
from app.research.datasets import DatasetRef

from .chapter_context import ChapterRows, PlacePoint, StoredExplainer
from .region_story import LayerOffer, RegionOffer

__all__ = ["CHAPTER_INPUTS_SCHEMA_VERSION", "ChapterInputs", "chapter_inputs", "inputs_rows"]

CHAPTER_INPUTS_SCHEMA_VERSION = 1


class InputLayer(ContractModel):
    id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    dataset_code: str = Field(min_length=1)


class InputRainfall(ContractModel):
    rain: MonthlyRain
    dataset_code: str = Field(min_length=1)


class InputPoint(ContractModel):
    wikidata_id: str = Field(pattern=r"^Q[1-9]\d*$")
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)


class InputExplainer(ContractModel):
    term_key: str = Field(min_length=1)
    piece_id: uuid.UUID
    golden: str = Field(pattern=r"^explainer\.[a-z0-9.-]+\.golden\.json$")


class ChapterInputs(ContractModel):
    schema_version: Literal[1]
    districts: list[DistrictRef]
    craft_districts: list[int]
    datasets: list[DatasetRef]
    layers: list[InputLayer]
    trends: list[ClimateTrend]
    series: list[ClimateSeries]
    rainfall: InputRainfall | None
    conformers: list[int]
    points: list[InputPoint]
    explainers: list[InputExplainer]


def chapter_inputs(path: Path) -> ChapterInputs:
    return ChapterInputs.model_validate_json(path.read_text(encoding="utf-8"))


def inputs_rows(inputs: ChapterInputs, rows: ChapterRows, *, goldens: Path) -> ChapterRows:
    datasets = {dataset.code: dataset for dataset in inputs.datasets}
    districts = {district.district_lgd: district for district in inputs.districts}
    region = RegionOffer(
        craft_districts=tuple(inputs.craft_districts),
        rivers=(),
        districts=districts,
        layers=tuple(LayerOffer(layer.id, layer.title, layer.dataset_code) for layer in inputs.layers),
        datasets=datasets,
    )
    trend_codes = dict.fromkeys(trend.dataset_code for trend in inputs.trends)
    climate = ClimateTrends(tuple(inputs.trends), tuple(datasets[code] for code in trend_codes))
    rain = inputs.rainfall
    return replace(
        rows,
        region=region,
        climate=climate,
        series=tuple(inputs.series),
        rainfall=DistrictRainfall(rain.rain, datasets[rain.dataset_code]) if rain else None,
        conformers=frozenset(inputs.conformers),
        points={p.wikidata_id: PlacePoint(p.wikidata_id, p.latitude, p.longitude) for p in inputs.points},
        explainers=tuple(_explainer(item, goldens) for item in inputs.explainers),
        datasets={**rows.datasets, **datasets},
    )


def _explainer(item: InputExplainer, goldens: Path) -> StoredExplainer:
    stored = json.loads((goldens / item.golden).read_text(encoding="utf-8"))
    block = SimulationBlock.model_validate(stored["block"])
    sources = {row["id"]: SourceRef.model_validate(row) for row in stored["sources"]}
    return StoredExplainer(piece_id=item.piece_id, term_key=item.term_key, block=block, sources=sources)
