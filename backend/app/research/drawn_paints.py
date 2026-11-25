from __future__ import annotations

import re
from collections.abc import Iterator, Mapping
from dataclasses import dataclass
from xml.etree import ElementTree

from .drawing_roles import css_declarations, paint_roles
from .drawing_rules import local_name

__all__ = ["PAGE_TEXT", "SHAPE_TAGS", "DrawnPaints", "Paints", "Shape", "drawn_paints"]

SHAPE_TAGS = frozenset({"rect", "path", "circle", "ellipse", "line", "polygon", "polyline"})
DEFINITIONS = frozenset(
    {"defs", "pattern", "mask", "clipPath", "marker", "symbol", "linearGradient", "radialGradient", "filter"}
)
INHERITED = ("fill", "stroke", "color")
SHAPE_PAINTS = ("fill", "stroke")
COLOUR = "color"
STOP_COLOUR = "stop-color"
STOP_TAG = "stop"
USE_TAG = "use"
CURRENT_COLOUR = "currentcolor"
FROM_PARENT = frozenset({"inherit", "unset"})
PAGE_TEXT = "var(--ink-1)"
REFERENCE = re.compile(r"^url\(\s*#([\w.-]+)\s*\)\s*(.*)$")
HREFS = ("href", "{http://www.w3.org/1999/xlink}href", "xlink:href")
NOTHING_SEEN: frozenset[str] = frozenset()

Paints = Mapping[str, str]


@dataclass(frozen=True)
class Shape:
    element: ElementTree.Element
    paints: Paints


@dataclass(frozen=True)
class DrawnPaints:
    painted: Mapping[ElementTree.Element, Paints]
    defined: Mapping[str, ElementTree.Element]
    shapes: tuple[Shape, ...]
    uses: tuple[Shape, ...]

    def roles(self, value: str, paints: Paints) -> list[str]:
        return self._roles(value, paints, NOTHING_SEEN)

    def shown_roles(self) -> list[str]:
        found = [role for shape in self.shapes for role in self._shape_roles(shape.paints, NOTHING_SEEN)]
        return found + [role for use in self.uses for role in self._used_roles(use)]

    def _roles(self, value: str, paints: Paints, seen: frozenset[str]) -> list[str]:
        compact = " ".join(value.split())
        if compact.casefold() == CURRENT_COLOUR:
            return paint_roles(paints.get(COLOUR, PAGE_TEXT))
        reference = REFERENCE.match(compact)
        if reference is None:
            return paint_roles(compact)
        fallback = reference.group(2)
        return [*self._referenced(reference.group(1), seen), *self._roles(fallback, paints, seen)]

    def _referenced(self, identity: str, seen: frozenset[str]) -> list[str]:
        element = self.defined.get(identity)
        if element is None or identity in seen:
            return []
        within = seen | {identity}
        found = [
            role
            for inner in element.iter()
            for role in self._inner_roles(inner, self.painted.get(inner, {}), within)
        ]
        target = _target(element)
        return found + (self._referenced(target, within) if target else [])

    def _used_roles(self, use: Shape) -> list[str]:
        element = self.defined.get(_target(use.element) or "")
        if element is None:
            return []
        walked = _walk(element, use.paints, hidden=False)
        return [
            role for inner, paints, _ in walked for role in self._inner_roles(inner, paints, NOTHING_SEEN)
        ]

    def _inner_roles(self, inner: ElementTree.Element, paints: Paints, seen: frozenset[str]) -> list[str]:
        tag = local_name(inner.tag)
        if tag == STOP_TAG:
            return self._roles(_stop_colour(inner), paints, seen)
        return self._shape_roles(paints, seen) if tag in SHAPE_TAGS else []

    def _shape_roles(self, paints: Paints, seen: frozenset[str]) -> list[str]:
        return [role for name in SHAPE_PAINTS for role in self._roles(paints.get(name, ""), paints, seen)]


def drawn_paints(root: ElementTree.Element) -> DrawnPaints:
    painted: dict[ElementTree.Element, Paints] = {}
    shapes: list[Shape] = []
    uses: list[Shape] = []
    for element, paints, hidden in _walk(root, {COLOUR: PAGE_TEXT}, hidden=False):
        painted[element] = paints
        tag = local_name(element.tag)
        if not hidden and tag in SHAPE_TAGS:
            shapes.append(Shape(element, paints))
        elif not hidden and tag == USE_TAG:
            uses.append(Shape(element, paints))
    defined = {str(element.get("id")): element for element in root.iter() if element.get("id")}
    return DrawnPaints(painted, defined, tuple(shapes), tuple(uses))


def _walk(
    element: ElementTree.Element, inherited: Paints, *, hidden: bool
) -> Iterator[tuple[ElementTree.Element, Paints, bool]]:
    hidden = hidden or local_name(element.tag) in DEFINITIONS
    paints = {**inherited, **_own_paints(element)}
    yield element, paints, hidden
    for child in element:
        yield from _walk(child, paints, hidden=hidden)


def _own_paints(element: ElementTree.Element) -> dict[str, str]:
    given = {name: value for name, value in element.attrib.items() if name in INHERITED}
    given |= {
        name: value for name, value in css_declarations(element.get("style") or "") if name in INHERITED
    }
    return {name: value for name, value in given.items() if not _from_parent(name, value)}


def _from_parent(name: str, value: str) -> bool:
    folded = " ".join(value.split()).casefold()
    return folded in FROM_PARENT or (name == COLOUR and folded == CURRENT_COLOUR)


def _stop_colour(stop: ElementTree.Element) -> str:
    declared = dict(css_declarations(stop.get("style") or ""))
    return declared.get(STOP_COLOUR) or stop.get(STOP_COLOUR) or ""


def _target(element: ElementTree.Element) -> str | None:
    found = next((element.get(name) for name in HREFS if element.get(name)), None)
    return found.strip()[1:] if found and found.strip().startswith("#") else None
