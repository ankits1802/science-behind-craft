from __future__ import annotations

import re
from collections.abc import Callable, Iterator, Mapping
from dataclasses import dataclass
from xml.etree import ElementTree

from .drawing_roles import css_declarations
from .drawing_rules import local_name

__all__ = ["CUSTOM_PREFIX", "PAGE_TEXT", "SHAPE_TAGS", "DrawnPaints", "Paints", "Shape", "drawn_paints"]

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
CUSTOM_PREFIX = "--"
FROM_PARENT = frozenset({"inherit", "unset"})
PAGE_TEXT = "var(--ink-1)"
INVALID = "\x00"
VARIABLE = re.compile(r"var\(\s*(--[\w-]+)\s*(,?)", re.IGNORECASE)
VARIABLE_NAME = re.compile(r"var\(\s*--([\w-]+)", re.IGNORECASE)
CURRENT_COLOUR = re.compile(r"(?<![\w-])currentcolor(?![\w-])", re.IGNORECASE)
LOCAL_URL = re.compile(r"url\(\s*#([\w.-]+)\s*\)", re.IGNORECASE)
HREFS = ("href", "{http://www.w3.org/1999/xlink}href", "xlink:href")
NOTHING_SEEN: frozenset[str] = frozenset()

Paints = Mapping[str, str]
Lookup = Callable[[str], str | None]


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
        found = VARIABLE_NAME.findall(value)
        if CURRENT_COLOUR.search(value):
            colour = CURRENT_COLOUR.sub(" ", paints.get(COLOUR, PAGE_TEXT))
            found += self._roles(colour, paints, seen)
        for identity in LOCAL_URL.findall(value):
            found += self._referenced(identity, seen)
        return found

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
            return self._roles(_stop_colour(inner, paints), paints, seen)
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
    paints = _declared_paints(_own_paints(element), inherited)
    yield element, paints, hidden
    for child in element:
        yield from _walk(child, paints, hidden=hidden)


def _own_paints(element: ElementTree.Element) -> dict[str, str]:
    given = {name: value for name, value in element.attrib.items() if name in INHERITED}
    given |= {
        name: value
        for name, value in css_declarations(element.get("style") or "")
        if name in INHERITED or name.startswith(CUSTOM_PREFIX)
    }
    return given


def _declared_paints(own: Mapping[str, str], inherited: Paints) -> dict[str, str]:
    paints = dict(inherited)
    for name in own:
        value = _resolved(name, own, inherited, NOTHING_SEEN)
        if name.startswith(CUSTOM_PREFIX):
            paints[name] = value
        elif value != INVALID and " ".join(value.split()).casefold() not in FROM_PARENT:
            paints[name] = _own_colour(value, inherited) if name == COLOUR else value
    return paints


def _resolved(name: str, own: Mapping[str, str], inherited: Paints, within: frozenset[str]) -> str:
    if name in within:
        return INVALID
    return _substituted(own[name], lambda inner: _declared(inner, own, inherited, within | {name}))


def _declared(name: str, own: Mapping[str, str], inherited: Paints, within: frozenset[str]) -> str | None:
    return _resolved(name, own, inherited, within) if name in own else inherited.get(name)


def _substituted(value: str, lookup: Lookup) -> str:
    parts: list[str] = []
    at = 0
    while found := VARIABLE.search(value, at):
        end = _closing(value, value.index("(", found.start()))
        fallback = value[found.end() : end] if found.group(2) else None
        given = _variable(found.group(1), fallback, lookup)
        if given == INVALID:
            return INVALID
        parts += [value[at : found.start()], given]
        at = end + 1
    return "".join(parts) + value[at:]


def _variable(name: str, fallback: str | None, lookup: Lookup) -> str:
    given = lookup(name)
    instead = _substituted(fallback, lookup) if fallback is not None and fallback.strip() else INVALID
    if given is None:
        return f"var({name})" if instead == INVALID else f"var({name}) {instead}"
    return instead if given == INVALID else given


def _closing(text: str, opening: int) -> int:
    depth = 0
    for at in range(opening, len(text)):
        depth += {"(": 1, ")": -1}.get(text[at], 0)
        if depth == 0:
            return at
    return len(text)


def _own_colour(value: str, inherited: Paints) -> str:
    parent = inherited.get(COLOUR, PAGE_TEXT)
    return CURRENT_COLOUR.sub(lambda _: parent, value)


def _stop_colour(stop: ElementTree.Element, paints: Paints) -> str:
    declared = dict(css_declarations(stop.get("style") or ""))
    given = _substituted(declared.get(STOP_COLOUR) or stop.get(STOP_COLOUR) or "", paints.get)
    return "" if given == INVALID else given


def _target(element: ElementTree.Element) -> str | None:
    found = next((element.get(name) for name in HREFS if element.get(name)), None)
    return found.strip()[1:] if found and found.strip().startswith("#") else None
