from __future__ import annotations

from collections.abc import Mapping
from typing import Annotated, Any, Self

from pydantic import Field, model_validator
from pydantic.json_schema import SkipJsonSchema

from .base import ContractModel, absent, empty
from .component_specs_general import YEAR_MAX, YEAR_MIN, GeneralHead
from .component_specs_plates_parts import UnitRef
from .datasets import BOUNDARY_CAPTION, DatasetRef
from .terms import WIKIDATA_ID_PATTERN

__all__ = [
    "AREA_LAYERS",
    "DECLARED_MARK",
    "ENTRIES_MAX",
    "LAYERS_MAX",
    "PHYSICAL_LAYERS",
    "PLACES_MAX",
    "SERVER_PARTS",
    "TIMELINE_MAP",
    "DatedPlace",
    "DatedRoute",
    "DeclaredTimelineMapSpec",
    "FoundPlace",
    "TimelineMapPlace",
    "UndatedFact",
    "server_parts_sent",
]

TIMELINE_MAP = "timeline_map"
DECLARED_MARK = "places"
PLACES_MAX = 30
ENTRIES_MAX = 40
LAYERS_MAX = 3
PHYSICAL_LAYERS = ("relief", "rivers", "minerals")
AREA_LAYERS = ("relief",)
LAYER_PATTERN = r"^[a-z0-9]+(?:-[a-z0-9]+)*$"
FOUND_KEY = "found"
DATASETS_KEY = "datasets"
CAPTION_KEY = "boundaryCaption"
SERVER_PARTS = (FOUND_KEY, DATASETS_KEY, CAPTION_KEY)
ONE_WAY = (
    "a place is named one way: its Wikidata item (wikidata), its LGD district code (district), "
    "or a coordinate (longitude and latitude) with the unit that cites it (at)"
)
CITED_POINT = "a place given by coordinate has its longitude, its latitude and the unit at that cites them"

Year = Annotated[int, Field(ge=YEAR_MIN, le=YEAR_MAX)]
LayerName = Annotated[str, Field(pattern=LAYER_PATTERN, max_length=80)]


class FoundPlace(ContractModel):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    wikidata_id: str | None = Field(default=None, pattern=WIKIDATA_ID_PATTERN, exclude_if=absent)
    district_lgd: int | None = Field(default=None, ge=1, exclude_if=absent)


class TimelineMapPlace(ContractModel):
    name: UnitRef
    wikidata: str | None = Field(default=None, pattern=WIKIDATA_ID_PATTERN, exclude_if=absent)
    district: int | None = Field(default=None, ge=1, exclude_if=absent)
    longitude: float | None = Field(default=None, ge=-180, le=180, exclude_if=absent)
    latitude: float | None = Field(default=None, ge=-90, le=90, exclude_if=absent)
    at: UnitRef | None = Field(default=None, exclude_if=absent)
    home: bool = False
    found: SkipJsonSchema[FoundPlace | None] = Field(default=None, exclude_if=absent)

    @model_validator(mode="after")
    def _named_one_way(self) -> Self:
        pointed = (self.longitude, self.latitude, self.at)
        ways = (
            self.wikidata is not None,
            self.district is not None,
            any(part is not None for part in pointed),
        )
        if sum(ways) != 1:
            raise ValueError(ONE_WAY)
        if ways[2] and any(part is None for part in pointed):
            raise ValueError(CITED_POINT)
        return self

    def reference(self) -> str:
        if self.wikidata is not None:
            return f"wikidata:{self.wikidata}"
        if self.district is not None:
            return f"district:{self.district}"
        return f"point:{self.longitude:g},{self.latitude:g}"


class DatedPlace(ContractModel):
    place: int = Field(ge=0)
    year_from: Year
    year_to: Year
    text: UnitRef

    @model_validator(mode="after")
    def _in_order(self) -> Self:
        if self.year_from > self.year_to:
            raise ValueError("a dated place's yearFrom is not after its yearTo")
        return self


class DatedRoute(ContractModel):
    start: int = Field(ge=0)
    end: int = Field(ge=0)
    year_from: Year
    year_to: Year
    text: UnitRef

    @model_validator(mode="after")
    def _between_two_places(self) -> Self:
        if self.start == self.end:
            raise ValueError("a route joins two different places")
        if self.year_from > self.year_to:
            raise ValueError("a route's yearFrom is not after its yearTo")
        return self


class UndatedFact(ContractModel):
    place: int | None = Field(default=None, ge=0)
    text: UnitRef


class DeclaredTimelineMapSpec(ContractModel):
    head: GeneralHead
    places: list[TimelineMapPlace] = Field(min_length=1, max_length=PLACES_MAX)
    points: list[DatedPlace] = Field(default_factory=list, max_length=ENTRIES_MAX, exclude_if=empty)
    routes: list[DatedRoute] = Field(default_factory=list, max_length=ENTRIES_MAX, exclude_if=empty)
    undated: list[UndatedFact] = Field(default_factory=list, max_length=ENTRIES_MAX, exclude_if=empty)
    layers: list[LayerName] = Field(default_factory=list, max_length=LAYERS_MAX, exclude_if=empty)
    datasets: SkipJsonSchema[list[DatasetRef]] = Field(default_factory=list, exclude_if=empty)
    boundary_caption: SkipJsonSchema[str | None] = Field(default=None, max_length=300, exclude_if=absent)

    @model_validator(mode="after")
    def _a_map_of_its_places(self) -> Self:
        problems = [*_entry_problems(self), *_layer_problems(self.layers)]
        if self.boundary_caption not in (None, BOUNDARY_CAPTION):
            problems.append("a timeline map is drawn under the Survey of India boundary caption")
        if problems:
            raise ValueError("; ".join(problems))
        return self

    def used_places(self) -> list[int]:
        used = [point.place for point in self.points]
        used += [index for route in self.routes for index in (route.start, route.end)]
        return used + [fact.place for fact in self.undated if fact.place is not None]


def server_parts_sent(spec: Mapping[str, Any]) -> bool:
    places = spec.get(DECLARED_MARK)
    sent = isinstance(places, list) and any(isinstance(p, Mapping) and FOUND_KEY in p for p in places)
    return sent or DATASETS_KEY in spec or CAPTION_KEY in spec


def _entry_problems(spec: DeclaredTimelineMapSpec) -> list[str]:
    if not (spec.points or spec.routes or spec.undated):
        return ["a timeline map dates, joins or captions its places with points, routes or undated facts"]
    used = spec.used_places()
    if any(index >= len(spec.places) for index in used):
        return ["a timeline map's points, routes and undated facts name only its listed places"]
    problems = []
    if set(used) != set(range(len(spec.places))):
        problems.append("each listed place is named by a point, a route or an undated fact")
    references = [place.reference() for place in spec.places]
    if len(set(references)) != len(references):
        problems.append("a timeline map lists each place once")
    return problems


def _layer_problems(layers: list[str]) -> list[str]:
    if len(set(layers)) != len(layers):
        return ["a timeline map names each layer once"]
    areas = [layer for layer in layers if layer in AREA_LAYERS or layer not in PHYSICAL_LAYERS]
    if len(areas) > 1:
        return [f"a timeline map shades one area layer at a time, not {', '.join(areas)}"]
    return []
