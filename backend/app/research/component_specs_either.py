from __future__ import annotations

from collections.abc import Mapping
from types import MappingProxyType
from typing import Annotated, Any

from pydantic import BaseModel, Discriminator, RootModel, Tag

from .base import ContractModel
from .component_specs_data import ChartSpec, FactTableSpec, TimelineSpec
from .component_specs_data_lists import RelatedCraftsSpec
from .component_specs_data_maps import MapLayerSpec, TimelineMapSpec
from .component_specs_general import (
    GENERAL_CHART,
    GENERAL_MAP_LAYER,
    GENERAL_TABLE,
    GENERAL_TIMELINE,
    GeneralChartSpec,
    GeneralMapLayerSpec,
    GeneralTableSpec,
    GeneralTimelineSpec,
    is_declared,
)
from .component_specs_timeline_map import DECLARED_MARK, TIMELINE_MAP, DeclaredTimelineMapSpec
from .kin_crafts import KIN_KIND, KinCraftsSpec

__all__ = [
    "AUTHORED",
    "DECLARED",
    "DECLARED_MARKS",
    "DELIVERED_FORMS",
    "EITHER_FORMS",
    "SPEC_MODELS_EITHER",
    "ChartKindSpec",
    "FactTableKindSpec",
    "MapLayerKindSpec",
    "RelatedCraftsKindSpec",
    "TimelineKindSpec",
    "TimelineMapKindSpec",
    "declared_form",
    "form_model",
    "spec_form",
]

AUTHORED = "authored"
DECLARED = "declared"
DECLARED_MARKS: Mapping[str, str] = MappingProxyType({TIMELINE_MAP: DECLARED_MARK})
DELIVERED_FORMS: Mapping[str, type[ContractModel]] = MappingProxyType({TIMELINE_MAP: DeclaredTimelineMapSpec})


def spec_form(value: Any) -> str:
    return DECLARED if is_declared(value) else AUTHORED


def declared_form(kind: str, spec: Any) -> bool:
    mark = DECLARED_MARKS.get(kind)
    if mark is None:
        return is_declared(spec)
    if isinstance(spec, Mapping):
        return mark in spec
    return isinstance(spec, DELIVERED_FORMS[kind])


def timeline_map_form(value: Any) -> str:
    return DECLARED if declared_form(TIMELINE_MAP, value) else AUTHORED


class ChartKindSpec(
    RootModel[
        Annotated[
            Annotated[GeneralChartSpec, Tag(DECLARED)] | Annotated[ChartSpec, Tag(AUTHORED)],
            Discriminator(spec_form),
        ]
    ]
):
    pass


class FactTableKindSpec(
    RootModel[
        Annotated[
            Annotated[GeneralTableSpec, Tag(DECLARED)] | Annotated[FactTableSpec, Tag(AUTHORED)],
            Discriminator(spec_form),
        ]
    ]
):
    pass


class TimelineKindSpec(
    RootModel[
        Annotated[
            Annotated[GeneralTimelineSpec, Tag(DECLARED)] | Annotated[TimelineSpec, Tag(AUTHORED)],
            Discriminator(spec_form),
        ]
    ]
):
    pass


class MapLayerKindSpec(
    RootModel[
        Annotated[
            Annotated[GeneralMapLayerSpec, Tag(DECLARED)] | Annotated[MapLayerSpec, Tag(AUTHORED)],
            Discriminator(spec_form),
        ]
    ]
):
    pass


class RelatedCraftsKindSpec(
    RootModel[
        Annotated[
            Annotated[KinCraftsSpec, Tag(DECLARED)] | Annotated[RelatedCraftsSpec, Tag(AUTHORED)],
            Discriminator(spec_form),
        ]
    ]
):
    pass


class TimelineMapKindSpec(
    RootModel[
        Annotated[
            Annotated[DeclaredTimelineMapSpec, Tag(DECLARED)] | Annotated[TimelineMapSpec, Tag(AUTHORED)],
            Discriminator(timeline_map_form),
        ]
    ]
):
    pass


EITHER_FORMS: Mapping[str, Mapping[str, type[ContractModel]]] = MappingProxyType(
    {
        GENERAL_CHART: MappingProxyType({DECLARED: GeneralChartSpec, AUTHORED: ChartSpec}),
        GENERAL_TABLE: MappingProxyType({DECLARED: GeneralTableSpec, AUTHORED: FactTableSpec}),
        GENERAL_TIMELINE: MappingProxyType({DECLARED: GeneralTimelineSpec, AUTHORED: TimelineSpec}),
        GENERAL_MAP_LAYER: MappingProxyType({DECLARED: GeneralMapLayerSpec, AUTHORED: MapLayerSpec}),
        KIN_KIND: MappingProxyType({DECLARED: KinCraftsSpec, AUTHORED: RelatedCraftsSpec}),
        TIMELINE_MAP: MappingProxyType({DECLARED: DeclaredTimelineMapSpec, AUTHORED: TimelineMapSpec}),
    }
)
SPEC_MODELS_EITHER: Mapping[str, type[BaseModel]] = MappingProxyType(
    {
        GENERAL_CHART: ChartKindSpec,
        GENERAL_TABLE: FactTableKindSpec,
        GENERAL_TIMELINE: TimelineKindSpec,
        GENERAL_MAP_LAYER: MapLayerKindSpec,
        KIN_KIND: RelatedCraftsKindSpec,
        TIMELINE_MAP: TimelineMapKindSpec,
    }
)


def form_model(kind: str, spec: Any) -> type[ContractModel] | None:
    forms = EITHER_FORMS.get(kind)
    return None if forms is None else forms[DECLARED if declared_form(kind, spec) else AUTHORED]
