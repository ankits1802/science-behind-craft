from __future__ import annotations

import re
from collections.abc import Mapping
from types import MappingProxyType

from .export_stills import (
    IDENTITY,
    WHITE,
    Affine,
    Colour,
    hex_colour,
    ink,
    mixed,
    rotated,
    scaled,
    token_colour,
    translated,
)

__all__ = ["BLACK", "length", "numbers", "paint_colour", "parsed_transform", "shown_colour"]

BLACK: Colour = (0, 0, 0)
NAMED: Mapping[str, Colour] = MappingProxyType({"black": BLACK, "white": WHITE})
NONE = "none"
CURRENT = "currentColor"
NUMBER = re.compile(r"[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?")
TOKEN = re.compile(r"^var\((--[a-z0-9-]+)\)$")
MIX = re.compile(r"^color-mix\(in srgb,\s*(.+?)\s+(\d{1,3})%,\s*(.+)\)$")
RGB = re.compile(r"^rgba?\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*(?:,\s*([\d.]+)\s*)?\)$")
URL = re.compile(r"^url\(#([\w-]+)\)$")
TRANSFORM = re.compile(r"(matrix|translate|scale|rotate)\s*\(([^)]*)\)")
PERCENT = 100.0


def numbers(text: str) -> list[float]:
    return [float(value) for value in NUMBER.findall(text)]


def length(text: str | None, default: float = 0.0) -> float:
    if text is None:
        return default
    found = NUMBER.match(text.strip())
    return float(found.group()) if found else default


def paint_colour(value: str | None, gradients: Mapping[str, Colour]) -> tuple[Colour | None, float]:
    if value is None:
        return None, 1.0
    text = value.strip()
    if text == NONE or not text:
        return None, 1.0
    if text == CURRENT:
        return ink(1), 1.0
    if text.startswith("#"):
        return _hex(text), 1.0
    if text in NAMED:
        return NAMED[text], 1.0
    return _functional(text, gradients)


def shown_colour(colour: Colour | None, alpha: float) -> Colour | None:
    if colour is None or alpha <= 0:
        return None
    return colour if alpha >= 1 else mixed(colour, alpha, WHITE)


def parsed_transform(text: str | None) -> Affine:
    result = IDENTITY
    for name, arguments in TRANSFORM.findall(text or ""):
        result = _transform(name, numbers(arguments)).then(result)
    return result


def _hex(text: str) -> Colour | None:
    try:
        return hex_colour(text)
    except ValueError:
        return None


def _functional(text: str, gradients: Mapping[str, Colour]) -> tuple[Colour | None, float]:
    token = TOKEN.match(text)
    if token:
        return token_colour(token.group(1)), 1.0
    mix = MIX.match(text)
    if mix:
        first, _ = paint_colour(mix.group(1), gradients)
        second, _ = paint_colour(mix.group(3), gradients)
        if first is None or second is None:
            return first or second, 1.0
        return mixed(first, int(mix.group(2)) / PERCENT, second), 1.0
    rgb = RGB.match(text)
    if rgb:
        alpha = float(rgb.group(4)) if rgb.group(4) else 1.0
        return (int(rgb.group(1)), int(rgb.group(2)), int(rgb.group(3))), alpha
    url = URL.match(text)
    if url:
        return gradients.get(url.group(1)), 1.0
    return None, 1.0


def _transform(name: str, values: list[float]) -> Affine:
    if name == "matrix" and len(values) == 6:
        return Affine(*values)
    if name == "translate" and values:
        return translated(values[0], values[1] if len(values) > 1 else 0.0)
    if name == "scale" and values:
        return scaled(values[0], values[1] if len(values) > 1 else None)
    if name == "rotate" and values:
        centre = (values[1], values[2]) if len(values) == 3 else (0.0, 0.0)
        return rotated(values[0], *centre)
    return IDENTITY
