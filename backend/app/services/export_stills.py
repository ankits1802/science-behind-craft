from __future__ import annotations

import math
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, replace
from functools import cache
from typing import Literal

from app.data.design_palette import design_palettes

__all__ = [
    "IDENTITY",
    "LIGHT_THEME",
    "WHITE",
    "Affine",
    "Anchor",
    "Colour",
    "Point",
    "Still",
    "StillPath",
    "StillText",
    "ellipse_points",
    "fitted",
    "hex_colour",
    "ink",
    "merged",
    "mixed",
    "placed",
    "rect_points",
    "rotated",
    "scaled",
    "token_colour",
    "translated",
]

LIGHT_THEME = "light"
TOKEN_PREFIX = "--"
ALIAS_PREFIX = "c-"
CIRCLE_STEPS = 36
WHITE: tuple[int, int, int] = (255, 255, 255)
INK_LEVELS = ("ink-1", "ink-2", "ink-3")

Colour = tuple[int, int, int]
Point = tuple[float, float]
Anchor = Literal["start", "middle", "end"]


@dataclass(frozen=True)
class Affine:
    a: float = 1.0
    b: float = 0.0
    c: float = 0.0
    d: float = 1.0
    e: float = 0.0
    f: float = 0.0

    def apply(self, point: Point) -> Point:
        x, y = point
        return self.a * x + self.c * y + self.e, self.b * x + self.d * y + self.f

    def then(self, outer: Affine) -> Affine:
        return Affine(
            a=outer.a * self.a + outer.c * self.b,
            b=outer.b * self.a + outer.d * self.b,
            c=outer.a * self.c + outer.c * self.d,
            d=outer.b * self.c + outer.d * self.d,
            e=outer.a * self.e + outer.c * self.f + outer.e,
            f=outer.b * self.e + outer.d * self.f + outer.f,
        )

    @property
    def scale(self) -> float:
        return math.sqrt(abs(self.a * self.d - self.b * self.c))


IDENTITY = Affine()


@dataclass(frozen=True)
class StillPath:
    points: tuple[Point, ...]
    closed: bool = True
    fill: Colour | None = None
    line: Colour | None = None
    width: float = 1.0


@dataclass(frozen=True)
class StillText:
    at: Point
    text: str
    size: float
    colour: Colour
    anchor: Anchor = "start"


@dataclass(frozen=True)
class Still:
    width: float
    height: float
    paths: tuple[StillPath, ...] = ()
    texts: tuple[StillText, ...] = ()

    @property
    def drawn(self) -> bool:
        return bool(self.paths or self.texts)


def translated(dx: float, dy: float) -> Affine:
    return Affine(e=dx, f=dy)


def scaled(sx: float, sy: float | None = None) -> Affine:
    return Affine(a=sx, d=sx if sy is None else sy)


def rotated(degrees: float, cx: float = 0.0, cy: float = 0.0) -> Affine:
    angle = math.radians(degrees)
    cos, sin = math.cos(angle), math.sin(angle)
    turn = Affine(a=cos, b=sin, c=-sin, d=cos)
    return translated(-cx, -cy).then(turn).then(translated(cx, cy))


def placed(still: Still, affine: Affine) -> Still:
    paths = tuple(
        replace(
            path, points=tuple(affine.apply(point) for point in path.points), width=path.width * affine.scale
        )
        for path in still.paths
    )
    texts = tuple(
        replace(text, at=affine.apply(text.at), size=text.size * affine.scale) for text in still.texts
    )
    return replace(still, paths=paths, texts=texts)


def merged(width: float, height: float, pieces: Iterable[tuple[Still, Affine]]) -> Still:
    shown = [placed(still, affine) for still, affine in pieces]
    return Still(
        width=width,
        height=height,
        paths=tuple(path for still in shown for path in still.paths),
        texts=tuple(text for still in shown for text in still.texts),
    )


def fitted(still: Still, width: float, height: float) -> Affine:
    if still.width <= 0 or still.height <= 0:
        return IDENTITY
    scale = min(width / still.width, height / still.height)
    left = (width - still.width * scale) / 2
    top = (height - still.height * scale) / 2
    return scaled(scale).then(translated(left, top))


def rect_points(x: float, y: float, width: float, height: float) -> tuple[Point, ...]:
    return (x, y), (x + width, y), (x + width, y + height), (x, y + height)


def ellipse_points(cx: float, cy: float, rx: float, ry: float) -> tuple[Point, ...]:
    return tuple(
        (
            cx + rx * math.cos(2 * math.pi * at / CIRCLE_STEPS),
            cy + ry * math.sin(2 * math.pi * at / CIRCLE_STEPS),
        )
        for at in range(CIRCLE_STEPS)
    )


def hex_colour(value: str) -> Colour:
    text = value.strip().lstrip("#")
    if len(text) == 3:
        text = "".join(char * 2 for char in text)
    if len(text) != 6:
        raise ValueError(f"{value!r} is not a hex colour")
    return int(text[0:2], 16), int(text[2:4], 16), int(text[4:6], 16)


@cache
def token_colour(token: str) -> Colour | None:
    name = token.strip().removeprefix(TOKEN_PREFIX)
    palette = design_palettes()[LIGHT_THEME]
    found = palette.get(name) or palette.get(name.removeprefix(ALIAS_PREFIX))
    return None if found is None else hex_colour(found)


def ink(level: int = 1) -> Colour:
    found = token_colour(f"{TOKEN_PREFIX}{INK_LEVELS[level - 1]}")
    if found is None:
        raise ValueError(f"the design system names no {INK_LEVELS[level - 1]}")
    return found


def mixed(first: Colour, share: float, second: Colour) -> Colour:
    kept = min(1.0, max(0.0, share))
    channels: Sequence[float] = [
        kept * one + (1 - kept) * two for one, two in zip(first, second, strict=True)
    ]
    return round(channels[0]), round(channels[1]), round(channels[2])
