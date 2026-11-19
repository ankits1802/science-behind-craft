from __future__ import annotations

from collections.abc import Mapping
from types import MappingProxyType
from typing import Literal, Self

from pydantic import Field, model_validator

from .base import ContractModel
from .component_specs_data_lists import (
    CitationToolSpec,
    ConceptAtlasSpec,
    RelatedCraftsSpec,
    SourceDisagreementsSpec,
    SourceListSpec,
)
from .component_specs_data_maps import MapLayerSpec, MapSequenceSpec, TimelineMapSpec
from .component_specs_data_parts import CssLength, FigureHead, FigureNumber, Placed, TextLine
from .component_specs_plates_parts import ClassName, DomId, DrawingElement, UnitRef

__all__ = [
    "CHART_FORMS",
    "SPEC_MODELS_DATA",
    "ChartSpec",
    "FactTableSpec",
    "StatTilesSpec",
    "TimelineSpec",
]

CHART_FORMS = ("drawing", "dots", "rows", "figure", "series")
CSV_PREFIX = "data:text/csv"


class DotsChart(ContractModel):
    classes: list[ClassName] = Field(min_length=1)
    label: str = Field(min_length=1)
    total: int = Field(ge=1)
    marked: int = Field(ge=0)

    @model_validator(mode="after")
    def _marks_within_the_total(self) -> Self:
        if self.marked > self.total:
            raise ValueError("A dot chart marks no more dots than it draws")
        return self


class BarRow(ContractModel):
    label: str = Field(min_length=1)
    value: float = Field(gt=0)
    shown: str = Field(min_length=1)
    emphasis: bool = False


class RowsChart(ContractModel):
    classes: list[ClassName] = Field(min_length=1)
    head: FigureHead
    rows: list[BarRow] = Field(min_length=1)
    source: UnitRef


class FigureChart(ContractModel):
    classes: list[ClassName] = Field(min_length=1)
    head: FigureHead
    drawing: DrawingElement
    source: TextLine


class SeriesTableRow(ContractModel):
    head: UnitRef
    cells: list[UnitRef | None] = Field(min_length=1)


class SeriesTable(ContractModel):
    summary: str = Field(min_length=1)
    caption: str = Field(min_length=1)
    head: list[UnitRef] = Field(min_length=1)
    rows: list[SeriesTableRow] = Field(min_length=1)


class SeriesDownload(ContractModel):
    href: str = Field(min_length=len(CSV_PREFIX) + 1)
    file_name: str = Field(pattern=r"^[A-Za-z0-9_.-]+\.csv$")
    label: str = Field(min_length=1)

    @model_validator(mode="after")
    def _a_table_of_values(self) -> Self:
        if not self.href.startswith(CSV_PREFIX):
            raise ValueError("A series download is its values as a CSV data link")
        return self


class SeriesPlot(ContractModel):
    classes: list[ClassName] = Field(min_length=1)
    label: str = Field(min_length=1)
    comp: str = Field(pattern=r"^[a-z]+$")
    series: list[list[int | float]] = Field(min_length=1)
    drawing: DrawingElement
    labels: list[Placed] = Field(default_factory=list)


class SeriesChart(ContractModel):
    classes: list[ClassName] = Field(min_length=1)
    head: FigureHead
    plot: SeriesPlot
    events: list[UnitRef] = Field(default_factory=list)
    table: SeriesTable
    download: SeriesDownload
    source: UnitRef


class ChartSpec(ContractModel):
    form: Literal[*CHART_FORMS]
    drawing: DrawingElement | None = None
    dots: DotsChart | None = None
    rows: RowsChart | None = None
    figure: FigureChart | None = None
    series: SeriesChart | None = None

    @model_validator(mode="after")
    def _the_part_of_its_form(self) -> Self:
        for form in CHART_FORMS:
            if (getattr(self, form) is not None) != (self.form == form):
                raise ValueError(f"A {self.form} chart has its {self.form} part and no other")
        return self


class StatTile(ContractModel):
    figure: str = Field(min_length=1)
    small: str | None = None
    caption: UnitRef


class StatTilesSpec(ContractModel):
    classes: list[ClassName] = Field(default_factory=list)
    tiles: list[StatTile] = Field(min_length=1)


class FactRow(ContractModel):
    term: UnitRef
    value: UnitRef


class FactTableSpec(ContractModel):
    id: DomId
    numeral: int = Field(ge=1)
    chapter_no: UnitRef
    title: UnitRef
    title_id: DomId
    rows: list[FactRow] = Field(min_length=1)


class ScaleMark(ContractModel):
    left: CssLength
    final: bool = False


class ScaleSpan(ContractModel):
    left: CssLength
    text: str = Field(min_length=1)


class ScaleTick(ContractModel):
    left: CssLength
    side: Literal["l", "mid", "r"]
    text: str = Field(min_length=1)


class TimelineScale(ContractModel):
    label: str = Field(min_length=1)
    marks: list[ScaleMark] = Field(min_length=2)
    spans: list[ScaleSpan] = Field(default_factory=list)
    ticks: list[ScaleTick] = Field(default_factory=list)


class TimelineSpec(ContractModel):
    variant: ClassName
    number: FigureNumber
    title: UnitRef
    scale: TimelineScale
    steps: list[UnitRef] = Field(min_length=1)


SPEC_MODELS_DATA: Mapping[str, type[ContractModel]] = MappingProxyType(
    {
        "chart": ChartSpec,
        "stat_tiles": StatTilesSpec,
        "fact_table": FactTableSpec,
        "map_layer": MapLayerSpec,
        "map_sequence": MapSequenceSpec,
        "timeline": TimelineSpec,
        "timeline_map": TimelineMapSpec,
        "concept_atlas": ConceptAtlasSpec,
        "related_crafts": RelatedCraftsSpec,
        "source_list": SourceListSpec,
        "source_disagreements": SourceDisagreementsSpec,
        "citation_tool": CitationToolSpec,
    }
)
