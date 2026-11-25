from __future__ import annotations

import re
from collections.abc import Iterator, Mapping
from dataclasses import dataclass
from typing import Any
from xml.etree import ElementTree

from .component_specs import MAP_POINTER
from .component_specs_general_svg import sanitised_svg
from .drawing_roles import css_declarations, paint_roles
from .drawing_rules import local_name
from .drawing_spec_rules import SVG_KEY, THEMES_KEY, node_element

__all__ = [
    "BASE_MAP_ROLES",
    "KIT_MAP_CLASSES",
    "MAPPED_KINDS",
    "OUTLINE_VERTICES_MIN",
    "PLACE_DOTS_MIN",
    "PLACE_ROLES",
    "drawn_map",
    "drawn_map_problems",
]

MAPPED_KINDS = frozenset({"drawing", "map_layer", "coded_figure"})
BASE_MAP_ROLES = frozenset(
    {
        "map-land",
        "map-land-foreign",
        "map-coast",
        "map-border-intl",
        "map-border-state",
        "map-border-district",
        "map-salt",
        "map-salt-hatch",
    }
)
PLACE_ROLES = frozenset({"terracotta", "map-marker", "map-marker-ring", "map-place"})
KIT_MAP_CLASSES = frozenset({"geo", "pin", "mk-disc", "mk-core", "mk-dot"})
KIT_PIN_ATTRIBUTE = "data-pin"
DOT_TAGS = frozenset({"circle", "ellipse"})
OUTLINE_TAGS = frozenset({"path", "polygon", "polyline"})
OUTLINE_ATTRIBUTES = ("d", "points")
PAINTS = frozenset({"fill", "stroke"})
SVG_TAG = "svg"
PLACE_DOTS_MIN = 2
OUTLINE_VERTICES_MIN = 60
NUMBER = re.compile(r"-?(?:\d+\.?\d*|\.\d+)(?:e-?\d+)?", re.IGNORECASE)
DRAWN_MAP = "the {kind} draws a map by hand: {reason}; {pointer}"
BASE_REASON = "it paints the base map's land, coast, borders or salt flats"
KIT_REASON = "it draws with the page kit's map frame and pins"
DOTS_REASON = "it marks {count} places as dots in the place colours"
OUTLINE_REASON = "it draws an outline of {vertices} points with {count} dots on it"


@dataclass(frozen=True)
class MapMarks:
    base: bool = False
    kit: bool = False
    place_dots: int = 0
    dots: int = 0
    outline: int = 0


def drawn_map(root: ElementTree.Element) -> str | None:
    marks = map_marks(root)
    if marks.base:
        return BASE_REASON
    if marks.kit:
        return KIT_REASON
    if marks.place_dots >= PLACE_DOTS_MIN:
        return DOTS_REASON.format(count=marks.place_dots)
    if marks.outline >= OUTLINE_VERTICES_MIN and marks.dots >= PLACE_DOTS_MIN:
        return OUTLINE_REASON.format(vertices=marks.outline, count=marks.dots)
    return None


def drawn_map_problems(kind: str, spec: Mapping[str, Any]) -> list[str]:
    if kind not in MAPPED_KINDS:
        return []
    for root in _drawings(spec):
        reason = drawn_map(root)
        if reason is not None:
            return [DRAWN_MAP.format(kind=kind, reason=reason, pointer=MAP_POINTER)]
    return []


def map_marks(root: ElementTree.Element) -> MapMarks:
    base, kit, place_dots, dots, outline = False, False, 0, 0, 0
    for element, roles in _painted(root, {}):
        tag = local_name(element.tag)
        base = base or bool(roles & BASE_MAP_ROLES)
        kit = kit or _kit_marked(element)
        if tag in DOT_TAGS:
            dots += 1
            place_dots += int(bool(roles & PLACE_ROLES))
        if tag in OUTLINE_TAGS:
            outline = max(outline, _vertices(element))
    return MapMarks(base=base, kit=kit, place_dots=place_dots, dots=dots, outline=outline)


def _kit_marked(element: ElementTree.Element) -> bool:
    classes = set((element.get("class") or "").split())
    return bool(classes & KIT_MAP_CLASSES) or KIT_PIN_ATTRIBUTE in element.attrib


def _drawings(spec: Mapping[str, Any]) -> Iterator[ElementTree.Element]:
    markup = spec.get(SVG_KEY)
    if isinstance(markup, str):
        yield ElementTree.fromstring(sanitised_svg(markup))
    yield from (node_element(node) for node in _svg_nodes(spec))


def _svg_nodes(value: Any) -> Iterator[Mapping[str, Any]]:
    if isinstance(value, Mapping):
        if value.get("tag") == SVG_TAG:
            yield value
            return
        for key, item in value.items():
            if key != THEMES_KEY:
                yield from _svg_nodes(item)
    elif isinstance(value, list):
        for item in value:
            yield from _svg_nodes(item)


def _painted(
    element: ElementTree.Element, inherited: Mapping[str, frozenset[str]]
) -> Iterator[tuple[ElementTree.Element, frozenset[str]]]:
    paints = {**inherited, **_own_paints(element)}
    yield element, frozenset[str]().union(*paints.values())
    for child in element:
        yield from _painted(child, paints)


def _own_paints(element: ElementTree.Element) -> dict[str, frozenset[str]]:
    found = {name: frozenset(paint_roles(value)) for name, value in element.attrib.items() if name in PAINTS}
    for name, value in css_declarations(element.get("style") or ""):
        if name in PAINTS:
            found[name] = frozenset(paint_roles(value))
    return found


def _vertices(element: ElementTree.Element) -> int:
    return max(len(NUMBER.findall(element.get(name) or "")) // 2 for name in OUTLINE_ATTRIBUTES)
