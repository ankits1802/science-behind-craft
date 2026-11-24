from __future__ import annotations

import math
import re
from collections.abc import Sequence
from dataclasses import dataclass, field

from .export_stills import Point

__all__ = ["CURVE_STEPS", "Subpath", "path_subpaths", "points_list"]

CURVE_STEPS = 12
TOKEN = re.compile(r"[MmLlHhVvCcSsQqTtAaZz]|[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?")
ARGUMENTS = {"M": 2, "L": 2, "H": 1, "V": 1, "C": 6, "S": 4, "Q": 4, "T": 2, "A": 7}
CLOSE = "Zz"
FULL_TURN = 2 * math.pi


@dataclass(frozen=True)
class Subpath:
    points: tuple[Point, ...]
    closed: bool


@dataclass
class _Pen:
    at: Point = (0.0, 0.0)
    start: Point = (0.0, 0.0)
    control: Point | None = None
    points: list[Point] = field(default_factory=list)
    done: list[Subpath] = field(default_factory=list)

    def move(self, point: Point) -> None:
        self._flush(closed=False)
        self.points = [point]
        self.at = self.start = point
        self.control = None

    def line(self, point: Point) -> None:
        if not self.points:
            self.points = [self.at]
        self.points.append(point)
        self.at = point

    def close(self) -> None:
        self._flush(closed=True)
        self.at = self.start
        self.control = None

    def finished(self) -> list[Subpath]:
        self._flush(closed=False)
        return self.done

    def _flush(self, *, closed: bool) -> None:
        if len(self.points) > 1:
            self.done.append(Subpath(tuple(self.points), closed))
        self.points = []


def path_subpaths(d: str) -> list[Subpath]:
    pen = _Pen()
    tokens = TOKEN.findall(d)
    at, command = 0, ""
    while at < len(tokens):
        if tokens[at].isalpha():
            command = tokens[at]
            at += 1
            if command in CLOSE:
                pen.close()
            continue
        count = ARGUMENTS.get(command.upper())
        values = tokens[at : at + (count or 0)]
        if count is None or len(values) < count or any(value.isalpha() for value in values):
            break
        at += count
        _draw(pen, command, [float(value) for value in values])
        command = {"M": "L", "m": "l"}.get(command, command)
    return pen.finished()


def points_list(text: str) -> tuple[Point, ...]:
    numbers = [float(value) for value in TOKEN.findall(text) if not value.isalpha()]
    return tuple(zip(numbers[0::2], numbers[1::2], strict=False))


def _draw(pen: _Pen, command: str, values: list[float]) -> None:
    upper = command.upper()
    absolute = _absolute(pen.at, command, values)
    if upper == "M":
        pen.move((absolute[0], absolute[1]))
    elif upper in "LHV":
        pen.line(_straight(pen.at, upper, absolute))
        pen.control = None
    elif upper in "CS":
        _cubic(pen, upper, absolute)
    elif upper in "QT":
        _quadratic(pen, upper, absolute)
    else:
        _arc(pen, absolute)
        pen.control = None


def _absolute(at: Point, command: str, values: list[float]) -> list[float]:
    if command.isupper():
        return values
    x, y = at
    upper = command.upper()
    if upper == "H":
        return [values[0] + x]
    if upper == "V":
        return [values[0] + y]
    if upper == "A":
        return [*values[:5], values[5] + x, values[6] + y]
    return [value + (x if index % 2 == 0 else y) for index, value in enumerate(values)]


def _straight(at: Point, upper: str, values: list[float]) -> Point:
    if upper == "H":
        return values[0], at[1]
    if upper == "V":
        return at[0], values[0]
    return values[0], values[1]


def _mirrored(pen: _Pen) -> Point:
    if pen.control is None:
        return pen.at
    return 2 * pen.at[0] - pen.control[0], 2 * pen.at[1] - pen.control[1]


def _cubic(pen: _Pen, upper: str, values: list[float]) -> None:
    if upper == "C":
        first, second, end = (values[0], values[1]), (values[2], values[3]), (values[4], values[5])
    else:
        first, second, end = _mirrored(pen), (values[0], values[1]), (values[2], values[3])
    start = pen.at
    for step in range(1, CURVE_STEPS + 1):
        t = step / CURVE_STEPS
        u = 1 - t
        pen.line(
            (
                u**3 * start[0] + 3 * u * u * t * first[0] + 3 * u * t * t * second[0] + t**3 * end[0],
                u**3 * start[1] + 3 * u * u * t * first[1] + 3 * u * t * t * second[1] + t**3 * end[1],
            )
        )
    pen.control = second


def _quadratic(pen: _Pen, upper: str, values: list[float]) -> None:
    if upper == "Q":
        control, end = (values[0], values[1]), (values[2], values[3])
    else:
        control, end = _mirrored(pen), (values[0], values[1])
    start = pen.at
    for step in range(1, CURVE_STEPS + 1):
        t = step / CURVE_STEPS
        u = 1 - t
        pen.line(
            (
                u * u * start[0] + 2 * u * t * control[0] + t * t * end[0],
                u * u * start[1] + 2 * u * t * control[1] + t * t * end[1],
            )
        )
    pen.control = control


def _arc(pen: _Pen, values: list[float]) -> None:
    rx, ry, turn, large, sweep, x, y = values
    end = (x, y)
    if rx == 0 or ry == 0 or end == pen.at:
        pen.line(end)
        return
    for point in _arc_points(pen.at, end, (abs(rx), abs(ry), turn), (large != 0, sweep != 0)):
        pen.line(point)


def _arc_points(
    start: Point, end: Point, radii: tuple[float, float, float], flags: tuple[bool, bool]
) -> list[Point]:
    rx, ry, turn = radii
    phi = math.radians(turn)
    cos, sin = math.cos(phi), math.sin(phi)
    half_x, half_y = (start[0] - end[0]) / 2, (start[1] - end[1]) / 2
    x1, y1 = cos * half_x + sin * half_y, -sin * half_x + cos * half_y
    grow = (x1 * x1) / (rx * rx) + (y1 * y1) / (ry * ry)
    if grow > 1:
        rx, ry = rx * math.sqrt(grow), ry * math.sqrt(grow)
    centre_x, centre_y = _arc_centre((x1, y1), (rx, ry), flags)
    cx = cos * centre_x - sin * centre_y + (start[0] + end[0]) / 2
    cy = sin * centre_x + cos * centre_y + (start[1] + end[1]) / 2
    first = _angle((1.0, 0.0), ((x1 - centre_x) / rx, (y1 - centre_y) / ry))
    sweep = _angle(
        ((x1 - centre_x) / rx, (y1 - centre_y) / ry), ((-x1 - centre_x) / rx, (-y1 - centre_y) / ry)
    )
    if not flags[1] and sweep > 0:
        sweep -= FULL_TURN
    elif flags[1] and sweep < 0:
        sweep += FULL_TURN
    angles = (first + sweep * step / CURVE_STEPS for step in range(1, CURVE_STEPS + 1))
    return [
        (
            cos * rx * math.cos(a) - sin * ry * math.sin(a) + cx,
            sin * rx * math.cos(a) + cos * ry * math.sin(a) + cy,
        )
        for a in angles
    ]


def _arc_centre(point: Point, radii: tuple[float, float], flags: tuple[bool, bool]) -> Point:
    x1, y1 = point
    rx, ry = radii
    above = rx * rx * ry * ry - rx * rx * y1 * y1 - ry * ry * x1 * x1
    below = rx * rx * y1 * y1 + ry * ry * x1 * x1
    factor = math.sqrt(max(0.0, above / below)) if below else 0.0
    if flags[0] == flags[1]:
        factor = -factor
    return factor * rx * y1 / ry, -factor * ry * x1 / rx


def _angle(first: Sequence[float], second: Sequence[float]) -> float:
    return math.atan2(
        first[0] * second[1] - first[1] * second[0], first[0] * second[0] + first[1] * second[1]
    )
