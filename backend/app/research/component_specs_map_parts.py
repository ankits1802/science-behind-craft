from __future__ import annotations

from collections.abc import Sequence
from typing import Annotated, Literal, Self

from pydantic import Field, model_validator

from .base import ContractModel, absent, empty
from .component_specs_plates_parts import UnitRef

__all__ = [
    "DAMS_EMPHASISED_MAX",
    "DISTRICT_VALUES_MAX",
    "DISTRICT_VALUES_MIN",
    "EMPHASIS_LAYERS",
    "RADIUS_KM_MAX",
    "RINGS_MAX",
    "RIVERS_EMPHASISED_MAX",
    "ROUTES_MAX",
    "STEPS_MAX",
    "STEPS_MIN",
    "DistrictValue",
    "MapDistricts",
    "MapEmphasis",
    "MapFrame",
    "MapParts",
    "MapRing",
    "MapRoute",
    "MapStep",
    "parts_problem",
]

ROUTES_MAX = 20
RINGS_MAX = 6
RADIUS_KM_MAX = 500.0
DISTRICT_VALUES_MAX = 60
DISTRICT_VALUES_MIN = 2
STEPS_MIN = 2
STEPS_MAX = 12
RIVERS_EMPHASISED_MAX = 6
DAMS_EMPHASISED_MAX = 6
INDEX_MAX = 60
EMPHASIS_LAYERS = ("relief", "rivers", "water")

Index = Annotated[int, Field(ge=0)]


class MapFrame(ContractModel):
    places: list[Index] | None = Field(default=None, min_length=1, max_length=INDEX_MAX, exclude_if=absent)
    district: int | None = Field(default=None, ge=1, exclude_if=absent)
    state: int | None = Field(default=None, ge=1, exclude_if=absent)

    @model_validator(mode="after")
    def _one_way(self) -> Self:
        named = [part for part in (self.places, self.district, self.state) if part is not None]
        if len(named) != 1:
            raise ValueError("A map's frame is chosen one way: from its places, or by a district or a state")
        return self


class MapEmphasis(ContractModel):
    layers: list[Literal[*EMPHASIS_LAYERS]] = Field(default_factory=list, max_length=len(EMPHASIS_LAYERS))
    rivers: list[str] = Field(default_factory=list, max_length=RIVERS_EMPHASISED_MAX)
    dams: list[str] = Field(default_factory=list, max_length=DAMS_EMPHASISED_MAX, exclude_if=empty)

    @model_validator(mode="after")
    def _something(self) -> Self:
        if not self.layers and not self.rivers and not self.dams:
            raise ValueError("An emphasis names a layer, a river or a dam")
        named = (self.layers, self.rivers, self.dams)
        if any(len(set(listed)) != len(listed) for listed in named):
            raise ValueError("An emphasis names each layer, river and dam once")
        return self


class MapRoute(ContractModel):
    start: int = Field(ge=0)
    end: int = Field(ge=0)
    text: UnitRef

    @model_validator(mode="after")
    def _moves(self) -> Self:
        if self.start == self.end:
            raise ValueError("A route runs between two different places")
        return self


class MapRing(ContractModel):
    place: int = Field(ge=0)
    radius_km: float = Field(gt=0, le=RADIUS_KM_MAX)
    text: UnitRef


class DistrictValue(ContractModel):
    district: int = Field(ge=1)
    value: float
    reading: UnitRef


class MapDistricts(ContractModel):
    value_label: UnitRef
    values: list[DistrictValue] = Field(min_length=DISTRICT_VALUES_MIN, max_length=DISTRICT_VALUES_MAX)

    @model_validator(mode="after")
    def _once(self) -> Self:
        codes = [value.district for value in self.values]
        if len(set(codes)) != len(codes):
            raise ValueError("A map gives each district one value")
        return self


class MapStep(ContractModel):
    text: UnitRef
    places: list[Index] = Field(default_factory=list, max_length=INDEX_MAX)
    routes: list[Index] = Field(default_factory=list, max_length=ROUTES_MAX)
    rings: list[Index] = Field(default_factory=list, max_length=RINGS_MAX)
    districts: bool = False

    @model_validator(mode="after")
    def _shows(self) -> Self:
        if not (self.places or self.routes or self.rings or self.districts):
            raise ValueError(
                "Each step of a map's sequence shows a place, a route, a ring or the district values"
            )
        return self


class MapParts(ContractModel):
    frame: MapFrame | None = Field(default=None, exclude_if=absent)
    emphasis: MapEmphasis | None = Field(default=None, exclude_if=absent)
    routes: list[MapRoute] | None = Field(
        default=None, min_length=1, max_length=ROUTES_MAX, exclude_if=absent
    )
    rings: list[MapRing] | None = Field(default=None, min_length=1, max_length=RINGS_MAX, exclude_if=absent)
    districts: MapDistricts | None = Field(default=None, exclude_if=absent)
    sequence: list[MapStep] | None = Field(
        default=None, min_length=STEPS_MIN, max_length=STEPS_MAX, exclude_if=absent
    )


def parts_problem(parts: MapParts, places: int) -> str | None:
    routes = parts.routes or []
    rings = parts.rings or []
    framed = (parts.frame.places or []) if parts.frame else []
    owned = [
        *(("the frame", index) for index in framed),
        *((f"route {at}", index) for at, route in enumerate(routes) for index in (route.start, route.end)),
        *((f"ring {at}", ring.place) for at, ring in enumerate(rings)),
        *((f"step {at}", index) for at, step in enumerate(parts.sequence or []) for index in step.places),
    ]
    for owner, index in owned:
        if index >= places:
            return f"{owner} names place {index}, past the map's {places} places"
    return _step_problem(parts.sequence or [], len(routes), len(rings), parts.districts is not None)


def _step_problem(steps: Sequence[MapStep], routes: int, rings: int, districts: bool) -> str | None:
    for at, step in enumerate(steps):
        if any(index >= routes for index in step.routes):
            return f"step {at} names a route past the map's {routes} routes"
        if any(index >= rings for index in step.rings):
            return f"step {at} names a ring past the map's {rings} rings"
        if step.districts and not districts:
            return f"step {at} shows the district values of a map that gives none"
    return None
