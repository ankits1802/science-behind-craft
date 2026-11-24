from __future__ import annotations

from collections.abc import Collection, Mapping

from .blocks import named_in_texts
from .component_specs_timeline_map import DeclaredTimelineMapSpec, TimelineMapPlace
from .quotes import numbers_in
from .timeline import states_movement, years_named

__all__ = ["SERVER_SENT", "timeline_map_problems"]

SERVER_SENT = (
    "the server resolves each place, credits the map's datasets and writes its boundary caption, so a "
    "timeline_map spec sends no found, datasets or boundaryCaption"
)


def timeline_map_problems(
    spec: DeclaredTimelineMapSpec, texts: Mapping[str, str], cited: Collection[str]
) -> list[str]:
    names = [texts.get(place.name, "") for place in spec.places]
    problems = [
        problem for at, place in enumerate(spec.places) for problem in _cited_point(at, place, texts, cited)
    ]
    return [*problems, *_dated_problems(spec, texts, names), *_undated_problems(spec, texts, names)]


def _cited_point(
    at: int, place: TimelineMapPlace, texts: Mapping[str, str], cited: Collection[str]
) -> list[str]:
    if place.at is None or place.longitude is None or place.latitude is None:
        return []
    stated = texts.get(place.at, "")
    problems = [
        f"the coordinate {value:g} of place {at} is not stated by its unit {place.at}"
        for value in (place.longitude, place.latitude)
        if not _states(stated, value)
    ]
    if place.at not in cited:
        problems.append(f"the unit {place.at} that places place {at} cites no fact")
    return problems


def _dated_problems(spec: DeclaredTimelineMapSpec, texts: Mapping[str, str], names: list[str]) -> list[str]:
    problems = []
    for at, point in enumerate(spec.points):
        text = texts.get(point.text, "")
        if (point.year_from, point.year_to) not in years_named([text]):
            problems.append(_years(f"point {at}", point.year_from, point.year_to, point.text))
        if not named_in_texts(names[point.place], [text]):
            problems.append(
                f"the unit {point.text} of point {at} does not name its place {names[point.place]!r}"
            )
    for at, route in enumerate(spec.routes):
        text = texts.get(route.text, "")
        if (route.year_from, route.year_to) not in years_named([text]):
            problems.append(_years(f"route {at}", route.year_from, route.year_to, route.text))
        start, end = names[route.start], names[route.end]
        if not states_movement([text], start, end):
            problems.append(
                f"the unit {route.text} of route {at} does not state the move from {start} to {end}"
            )
    return problems


def _undated_problems(spec: DeclaredTimelineMapSpec, texts: Mapping[str, str], names: list[str]) -> list[str]:
    return [
        f"the unit {fact.text} of undated fact {at} does not name its place {names[fact.place]!r}"
        for at, fact in enumerate(spec.undated)
        if fact.place is not None and not named_in_texts(names[fact.place], [texts.get(fact.text, "")])
    ]


def _years(owner: str, year_from: int, year_to: int, ref: str) -> str:
    return f"the years {year_from} to {year_to} of {owner} are not stated by its unit {ref}"


def _states(text: str, value: float) -> bool:
    for figure in numbers_in(text):
        try:
            if float(figure) == value:
                return True
        except ValueError:
            continue
    return False
