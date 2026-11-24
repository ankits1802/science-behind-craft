from __future__ import annotations

from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass, field, replace
from typing import Any, cast

from .export_still_paint import length, numbers, paint_colour, parsed_transform, shown_colour
from .export_still_paths import path_subpaths, points_list
from .export_stills import (
    IDENTITY,
    Affine,
    Anchor,
    Colour,
    Point,
    Still,
    StillPath,
    StillText,
    ellipse_points,
    rect_points,
    scaled,
    translated,
)

__all__ = ["SKIPPED_TAGS", "svg_still"]

SKIPPED_TAGS = frozenset(
    {
        "defs",
        "title",
        "desc",
        "clipPath",
        "mask",
        "marker",
        "pattern",
        "linearGradient",
        "radialGradient",
        "stop",
        "filter",
        "symbol",
        "use",
        "style",
        "feColorMatrix",
        "feComponentTransfer",
        "feFuncR",
        "feFuncG",
        "feFuncB",
        "feGaussianBlur",
    }
)
GRADIENTS = frozenset({"linearGradient", "radialGradient"})
GROUPS = frozenset({"g", "svg", "a"})
TEXTS = frozenset({"text", "tspan"})
ANCHORS: Mapping[str, Anchor] = {"start": "start", "middle": "middle", "end": "end"}
DEFAULT_FONT = 16.0
HIDDEN = (("display", "none"), ("visibility", "hidden"))


@dataclass(frozen=True)
class _Style:
    fill: str | None = "#000"
    stroke: str | None = None
    stroke_width: float = 1.0
    opacity: float = 1.0
    fill_opacity: float = 1.0
    stroke_opacity: float = 1.0
    font_size: float = DEFAULT_FONT
    anchor: Anchor = "start"
    affine: Affine = IDENTITY


@dataclass
class _Drawn:
    gradients: Mapping[str, Colour]
    paths: list[StillPath] = field(default_factory=list)
    texts: list[StillText] = field(default_factory=list)


def svg_still(node: Mapping[str, Any]) -> Still:
    attrs = _attrs(node)
    box = numbers(attrs.get("viewBox", ""))
    drawn = _Drawn(gradients=dict(_gradients(node)))
    root = _Style(affine=translated(-box[0], -box[1]) if len(box) == 4 else IDENTITY)
    if node.get("tag") in GROUPS:
        start = _styled(root, attrs, "g")
        for child in _children(node):
            _visit(child, start, drawn)
    else:
        _visit(node, root, drawn)
    if len(box) == 4:
        width, height = box[2], box[3]
    else:
        width, height = _extent(drawn.paths)
    return Still(width=width, height=height, paths=tuple(drawn.paths), texts=tuple(drawn.texts))


def _visit(node: Any, style: _Style, drawn: _Drawn) -> None:
    if not isinstance(node, Mapping):
        return
    tag = str(node.get("tag", ""))
    attrs = _attrs(node)
    if tag in SKIPPED_TAGS or any(attrs.get(name) == value for name, value in HIDDEN):
        return
    own = _styled(style, attrs, tag)
    if tag in TEXTS:
        _text(node, own, drawn)
        return
    if tag in GROUPS:
        for child in _children(node):
            _visit(child, own, drawn)
        return
    for points, closed in _outline(tag, attrs):
        _path(points, closed, own, drawn)


def _styled(style: _Style, attrs: Mapping[str, str], tag: str) -> _Style:
    affine = parsed_transform(attrs.get("transform")).then(style.affine)
    if tag == "svg" and "viewBox" in attrs:
        affine = _nested(attrs).then(affine)
    return replace(
        style,
        fill=attrs.get("fill", style.fill),
        stroke=attrs.get("stroke", style.stroke),
        stroke_width=length(attrs.get("stroke-width"), style.stroke_width),
        opacity=style.opacity * length(attrs.get("opacity"), 1.0),
        fill_opacity=length(attrs.get("fill-opacity"), style.fill_opacity),
        stroke_opacity=length(attrs.get("stroke-opacity"), style.stroke_opacity),
        font_size=length(attrs.get("font-size"), style.font_size),
        anchor=ANCHORS.get(attrs.get("text-anchor", ""), style.anchor),
        affine=affine,
    )


def _nested(attrs: Mapping[str, str]) -> Affine:
    box = numbers(attrs["viewBox"])
    if len(box) != 4 or box[2] <= 0 or box[3] <= 0:
        return IDENTITY
    width = length(attrs.get("width"), box[2])
    height = length(attrs.get("height"), box[3])
    inner = translated(-box[0], -box[1]).then(scaled(width / box[2], height / box[3]))
    return inner.then(translated(length(attrs.get("x")), length(attrs.get("y"))))


def _outline(tag: str, attrs: Mapping[str, str]) -> Iterator[tuple[Sequence[Point], bool]]:
    if tag == "path":
        for subpath in path_subpaths(attrs.get("d", "")):
            yield subpath.points, subpath.closed
    elif tag == "rect":
        yield rect_points(*(length(attrs.get(name)) for name in ("x", "y", "width", "height"))), True
    elif tag == "circle":
        r = length(attrs.get("r"))
        yield ellipse_points(length(attrs.get("cx")), length(attrs.get("cy")), r, r), True
    elif tag == "ellipse":
        values = (length(attrs.get(name)) for name in ("cx", "cy", "rx", "ry"))
        yield ellipse_points(*values), True
    elif tag == "line":
        ends = [length(attrs.get(name)) for name in ("x1", "y1", "x2", "y2")]
        yield ((ends[0], ends[1]), (ends[2], ends[3])), False
    elif tag in ("polyline", "polygon"):
        yield points_list(attrs.get("points", "")), tag == "polygon"


def _path(points: Sequence[Point], closed: bool, style: _Style, drawn: _Drawn) -> None:
    if len(points) < 2:
        return
    fill, fill_alpha = paint_colour(style.fill, drawn.gradients)
    line, line_alpha = paint_colour(style.stroke, drawn.gradients)
    shown_fill = (
        shown_colour(fill, fill_alpha * style.fill_opacity * style.opacity) if len(points) > 2 else None
    )
    shown_line = shown_colour(line, line_alpha * style.stroke_opacity * style.opacity)
    if shown_fill is None and shown_line is None:
        return
    drawn.paths.append(
        StillPath(
            points=tuple(style.affine.apply(point) for point in points),
            closed=closed,
            fill=shown_fill,
            line=shown_line,
            width=style.stroke_width * style.affine.scale,
        )
    )


def _text(node: Mapping[str, Any], style: _Style, drawn: _Drawn) -> None:
    attrs = _attrs(node)
    words = " ".join("".join(_strings(node)).split())
    colour = shown_colour(*paint_colour(style.fill, drawn.gradients))
    if not words or colour is None:
        return
    at = style.affine.apply((length(attrs.get("x")), length(attrs.get("y"))))
    size = style.font_size * style.affine.scale
    drawn.texts.append(StillText(at=at, text=words, size=size, colour=colour, anchor=style.anchor))


def _strings(node: Any) -> Iterator[str]:
    if isinstance(node, str):
        yield node
    elif isinstance(node, Mapping):
        for child in _children(node):
            yield from _strings(child)


def _gradients(node: Any) -> Iterator[tuple[str, Colour]]:
    if not isinstance(node, Mapping):
        return
    attrs = _attrs(node)
    if node.get("tag") in GRADIENTS and "id" in attrs:
        stops = [
            child for child in _children(node) if isinstance(child, Mapping) and child.get("tag") == "stop"
        ]
        colour = paint_colour(_attrs(stops[0]).get("stop-color"), {})[0] if stops else None
        if colour is not None:
            yield attrs["id"], colour
    for child in _children(node):
        yield from _gradients(child)


def _attrs(node: Mapping[str, Any]) -> Mapping[str, str]:
    attrs = node.get("attrs")
    return cast(Mapping[str, str], attrs) if isinstance(attrs, Mapping) else {}


def _children(node: Mapping[str, Any]) -> Sequence[Any]:
    children = node.get("children")
    return children if isinstance(children, list) else []


def _extent(paths: Sequence[StillPath]) -> tuple[float, float]:
    points = [point for path in paths for point in path.points]
    if not points:
        return 0.0, 0.0
    return max(x for x, _ in points), max(y for _, y in points)
