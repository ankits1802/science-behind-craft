from __future__ import annotations

import re

__all__ = [
    "REFERENCE_ATTRIBUTES",
    "STYLE_PROPERTIES",
    "drawing_attribute_problem",
    "loads_nothing",
    "style_problem",
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
REFERENCE_ATTRIBUTES = frozenset({"href", "xlink:href"})
REFUSED_ATTRIBUTES = frozenset({"cursor"})
EVENT_PREFIX = "on"
STYLE_ATTRIBUTE = "style"
LOCAL_REFERENCE = "#"
CUSTOM_PROPERTY = re.compile(r"--[a-z][a-z0-9-]*")
STYLE_VALUE = re.compile(r"[A-Za-z0-9\s.,%#()+_-]+")
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
REFERENCE = "refers only within its page (#id)"
CURSOR = "sets no cursor"
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
    return style_problem(value) if lowered == STYLE_ATTRIBUTE else None


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
