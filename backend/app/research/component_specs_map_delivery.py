from __future__ import annotations

from collections.abc import Collection, Mapping
from typing import Any

from .component_specs_general import GeneralMapLayerSpec
from .component_specs_map_parts import MapParts
from .quotes import states_value
from .timeline import states_movement

__all__ = ["map_layer_problems", "map_parts_problems"]


def map_layer_problems(spec: Any, texts: Mapping[str, str], cited: Collection[str]) -> list[str]:
    if not isinstance(spec, GeneralMapLayerSpec):
        return []
    names = [texts.get(place.name, "") for place in spec.places]
    return map_parts_problems(spec, names, texts, cited)


def map_parts_problems(
    parts: MapParts, names: list[str], texts: Mapping[str, str], cited: Collection[str]
) -> list[str]:
    return [
        *_route_problems(parts, names, texts, cited),
        *_ring_problems(parts, texts, cited),
        *_district_problems(parts, texts, cited),
        *_step_problems(parts, cited),
    ]


def _route_problems(
    parts: MapParts, names: list[str], texts: Mapping[str, str], cited: Collection[str]
) -> list[str]:
    problems = []
    for at, route in enumerate(parts.routes or []):
        start, end = names[route.start], names[route.end]
        if not states_movement([texts.get(route.text, "")], start, end):
            problems.append(
                f"the unit {route.text} of route {at} does not state the move from {start} to {end}"
            )
        problems += _uncited(route.text, f"route {at}", cited)
    return problems


def _ring_problems(parts: MapParts, texts: Mapping[str, str], cited: Collection[str]) -> list[str]:
    problems = []
    for at, ring in enumerate(parts.rings or []):
        if not states_value(texts.get(ring.text, ""), ring.radius_km):
            problems.append(
                f"the radius {ring.radius_km:g} km of ring {at} is not stated by its unit {ring.text}"
            )
        problems += _uncited(ring.text, f"ring {at}", cited)
    return problems


def _district_problems(parts: MapParts, texts: Mapping[str, str], cited: Collection[str]) -> list[str]:
    if parts.districts is None:
        return []
    problems = []
    for value in parts.districts.values:
        if not states_value(texts.get(value.reading, ""), value.value):
            problems.append(
                f"the value {value.value:g} of district {value.district} is not stated by its unit {value.reading}"
            )
        problems += _uncited(value.reading, f"district {value.district}", cited)
    return problems


def _step_problems(parts: MapParts, cited: Collection[str]) -> list[str]:
    return [
        problem
        for at, step in enumerate(parts.sequence or [])
        for problem in _uncited(step.text, f"step {at}", cited)
    ]


def _uncited(ref: str, owner: str, cited: Collection[str]) -> list[str]:
    return [] if ref in cited else [f"the unit {ref} of {owner} cites no fact"]
