from __future__ import annotations

import re
from collections.abc import Mapping

from .drawing_classes import DRAWING_CLASSES

__all__ = [
    "CLASS_ATTRIBUTES",
    "DRAWING_CLASSES",
    "REFERENCE_ATTRIBUTES",
    "STYLE_PROPERTIES",
    "drawing_attribute_problem",
    "loads_nothing",
    "style_problem",
    "svg_box_problem",
    "svg_view_box",
]

STYLE_PROPERTIES = frozenset(
    {
        "alignment-baseline",
        "baseline-shift",
        "clip-path",
        "clip-rule",
        "color",
        "color-interpolation",
        "color-interpolation-filters",
        "direction",
        "display",
        "dominant-baseline",
        "fill",
        "fill-opacity",
        "fill-rule",
        "flood-color",
        "flood-opacity",
        "font-family",
        "font-size",
        "font-stretch",
        "font-style",
        "font-variant",
        "font-weight",
        "image-rendering",
        "isolation",
        "letter-spacing",
        "lighting-color",
        "mix-blend-mode",
        "opacity",
        "paint-order",
        "pointer-events",
        "shape-rendering",
        "stop-color",
        "stop-opacity",
        "stroke",
        "stroke-dasharray",
        "stroke-dashoffset",
        "stroke-linecap",
        "stroke-linejoin",
        "stroke-miterlimit",
        "stroke-opacity",
        "stroke-width",
        "text-anchor",
        "text-decoration",
        "text-rendering",
        "transform",
        "transform-box",
        "transform-origin",
        "unicode-bidi",
        "vector-effect",
        "visibility",
        "white-space",
        "word-spacing",
        "writing-mode",
    }
)
CLASS_ATTRIBUTES = frozenset({"class", "classname"})
REFERENCE_ATTRIBUTES = frozenset({"href", "xlink:href"})
REFUSED_ATTRIBUTES = frozenset({"cursor"})
EVENT_PREFIX = "on"
STYLE_ATTRIBUTE = "style"
LOCAL_REFERENCE = "#"
CUSTOM_PROPERTY = re.compile(r"--[a-z][a-z0-9-]*")
STYLE_VALUE = re.compile(r"[A-Za-z0-9\s.,%#()+_-]+")
SVG_SIZE = re.compile(r"\s*(\d+(?:\.\d+)?)\s*(px|%)?\s*")
VIEW_BOX = re.compile(
    r"^\s*(-?\d+(?:\.\d+)?)[\s,]+(-?\d+(?:\.\d+)?)[\s,]+(\d+(?:\.\d+)?)[\s,]+(\d+(?:\.\d+)?)\s*$"
)
SHRINK = re.compile(r"\s*scale[XY]?\(\s*(\d*\.?\d+)\s*(?:[\s,]\s*(\d*\.?\d+)\s*)?\)\s*,?", re.IGNORECASE)
SVG_SIZES = frozenset({"width", "height"})
VIEW_BOX_ATTRIBUTE = "viewbox"
WHOLE_PERCENT = 100.0
WHOLE_SCALE = 1.0
AUTO = "auto"
NO_TRANSFORM = "none"
SHOWN_OVERFLOW = frozenset({"visible", "auto", "scroll"})
TRANSFORM = "transform"
OVERFLOW = "overflow"
MOVED_ORIGIN = frozenset({"transform-origin", "transform-box"})
FOREIGN_LOAD = re.compile(
    r"url\((?!\s*(['\"]?)#[\w.-]+\1\s*\))|image-set\(|cross-fade\(|(?<![\w-])(?:image|src)\(|\\",
    re.IGNORECASE,
)
SCRIPTED = re.compile(r"javascript:|expression\(|@import", re.IGNORECASE)

HANDLER = "runs no handler"
SCRIPT = "runs no script"
LOAD = (
    "loads nothing from another address: no url() but an in-drawing url(#id), no image-set(), "
    "cross-fade(), image() or src(), and no backslash escape"
)
REFERENCE = "refers only to its page (#id)"
CURSOR = "sets no cursor"
CLASS = "names only the classes the kit's own drawings carry, never a class of the site's"
BOX = (
    "is drawn within its box: an svg's width and height at most its viewBox's or 100%, a transform that only "
    "shrinks it about its own centre, and nothing shown past its edge"
)
DECLARATION = "holds style declarations of a property and its value"
PROPERTY = (
    "sets in its style only paint, stroke, opacity, transform, text, display and custom properties, "
    "never {name}"
)
VALUE = "gives {name} a token, a number or a keyword, never {value!r}"


def loads_nothing(value: str) -> bool:
    return not FOREIGN_LOAD.search(value) and not SCRIPTED.search("".join(value.split()))


def drawing_attribute_problem(name: str, value: str) -> str | None:
    lowered = name.lower()
    if lowered.startswith(EVENT_PREFIX):
        return HANDLER
    if SCRIPTED.search("".join(value.split())):
        return SCRIPT
    if FOREIGN_LOAD.search(value):
        return LOAD
    if lowered in REFERENCE_ATTRIBUTES and not value.startswith(LOCAL_REFERENCE):
        return REFERENCE
    if lowered in REFUSED_ATTRIBUTES:
        return CURSOR
    if lowered in CLASS_ATTRIBUTES and not set(value.split()) <= DRAWING_CLASSES:
        return CLASS
    return style_problem(value) if lowered == STYLE_ATTRIBUTE else None


def svg_view_box(value: str | None) -> tuple[float, float, float, float] | None:
    found = VIEW_BOX.match(value or "")
    if found is None:
        return None
    x, y, width, height = (float(part) for part in found.groups())
    return (x, y, width, height) if width > 0 and height > 0 else None


def svg_box_problem(attrs: Mapping[str, str]) -> str | None:
    given = [(name.lower(), value) for name, value in attrs.items()]
    box = svg_view_box(next((value for name, value in given if name == VIEW_BOX_ATTRIBUTE), None))
    bounds = {"width": box[2], "height": box[3]} if box else {}
    for name, value in given:
        declared = _style_declarations(value) if name == STYLE_ATTRIBUTE else [(name, value)]
        if any(_unbounded(prop, entry, bounds) for prop, entry in declared):
            return BOX
    return None


def _style_declarations(style: str) -> list[tuple[str, str]]:
    parts = (declaration.partition(":") for declaration in style.split(";"))
    return [(name.strip().lower(), value.strip()) for name, _, value in parts if name.strip()]


def _unbounded(name: str, value: str, bounds: Mapping[str, float]) -> bool:
    if name in SVG_SIZES:
        return not _within(value, bounds.get(name))
    if name == TRANSFORM:
        return not _shrinks(value)
    if name == OVERFLOW:
        return value.strip().lower() in SHOWN_OVERFLOW
    return name in MOVED_ORIGIN


def _within(value: str, bound: float | None) -> bool:
    if value.strip().lower() == AUTO:
        return True
    size = SVG_SIZE.fullmatch(value)
    if size is None:
        return False
    amount = float(size.group(1))
    if size.group(2) == "%":
        return amount <= WHOLE_PERCENT
    return bound is not None and amount <= bound


def _shrinks(transform: str) -> bool:
    text = transform.strip()
    if not text or text.lower() == NO_TRANSFORM:
        return True
    at = 0
    while at < len(text):
        found = SHRINK.match(text, at)
        if found is None or found.end() == at:
            return False
        if any(float(factor) > WHOLE_SCALE for factor in found.groups() if factor is not None):
            return False
        at = found.end()
    return True


def style_problem(style: str) -> str | None:
    for declaration in style.split(";"):
        if not declaration.strip():
            continue
        name, colon, value = declaration.partition(":")
        name, value = name.strip().lower(), value.strip()
        if not colon or not name or not value:
            return DECLARATION
        if name not in STYLE_PROPERTIES and not CUSTOM_PROPERTY.fullmatch(name):
            return PROPERTY.format(name=name)
        if not STYLE_VALUE.fullmatch(value):
            return VALUE.format(name=name, value=value)
    return None
