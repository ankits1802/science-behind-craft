from __future__ import annotations

import re
from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass
from typing import Any
from xml.etree import ElementTree

from .art_kit import KIT_PARTS, parts_named_by
from .component_specs_general_svg import sanitised_svg, svg_view_box
from .component_specs_science_parts import SVG_TAGS
from .drawing_roles import MATERIAL_ROLES, css_declarations, paint_roles
from .drawing_rules import DRAWN_WIDTH_MIN, TEXT_FLOOR_PX, drawn_texts, local_name
from .drawing_spec_rules import SVG_KEY, THEMES_KEY, node_element

__all__ = [
    "KIT_FIGURE_KINDS",
    "KIT_POINTER",
    "MATERIAL_PARTS",
    "MOLECULE_KINDS",
    "SHAPES_MIN",
    "SIZE_TOLERANCE_PX",
    "UI_SIZES_PX",
    "Drawn",
    "drawn_art_problems",
    "free_drawings",
]

MOLECULE_KINDS = frozenset({"structure_diagram", "molecule_3d"})
KIT_FIGURE_KINDS = frozenset({"drawing", "diagram"})
UI_SIZES_PX = (12, 13, 14, 16)
SIZE_TOLERANCE_PX = 0.25
SHAPES_MIN = 6
SHAPE_TAGS = frozenset({"rect", "path", "circle", "ellipse", "line", "polygon", "polyline"})
DEFINITIONS = frozenset(
    {"defs", "pattern", "mask", "clipPath", "marker", "symbol", "linearGradient", "radialGradient", "filter"}
)
WORDED = frozenset({"title", "desc"})
INK_ROLES = frozenset({"ink-1", "ink-2", "ink-3"})
CURRENT_COLOUR = "currentcolor"
PAINTS = ("fill", "stroke")
GEOMETRY = (
    "d",
    "points",
    "x",
    "y",
    "width",
    "height",
    "cx",
    "cy",
    "r",
    "rx",
    "ry",
    "x1",
    "y1",
    "x2",
    "y2",
    "transform",
)
LOCAL_URL = re.compile(r"^url\(#([\w.-]+)\)$")
ICON_KEY = re.compile(r"icon$", re.IGNORECASE)
DRAWING_KEY = "drawing"
SVG_TAG = "svg"
MATERIAL_FIELDS = frozenset({"material", "liquor", "layers.material"})
MATERIAL_PARTS = tuple(name for name, part in KIT_PARTS.items() if MATERIAL_FIELDS & set(part.materials))
KIT_POINTER = (
    "compose the figure from the kit instead: a diagram with a head, a layout and panels whose named parts "
    "the site draws (kalavigyan://components/diagram.schema.json)"
)
AT_THE_BAR = "draw it with more of its parts, edged in ink and textured, as the kit's parts are drawn"
Paints = Mapping[str, str]


@dataclass(frozen=True)
class Drawn:
    where: str
    root: ElementTree.Element


@dataclass(frozen=True)
class Shape:
    element: ElementTree.Element
    paints: Paints


def drawn_art_problems(kind: str, spec: Mapping[str, Any], texts: Mapping[str, str]) -> list[str]:
    if kind in MOLECULE_KINDS:
        return []
    found: list[str] = []
    for drawn in free_drawings(kind, spec):
        shapes = list(_shapes(drawn.root, {}))
        found += _type_problems(drawn)
        found += _structure_problems(drawn, shapes, kind)
        if kind in KIT_FIGURE_KINDS:
            found += _kit_problems(drawn, shapes, _words(drawn.root, spec, texts))
        else:
            found += _texture_problems(drawn, shapes)
    return list(dict.fromkeys(found))


def free_drawings(kind: str, spec: Mapping[str, Any]) -> Iterator[Drawn]:
    markup = spec.get(SVG_KEY)
    if isinstance(markup, str):
        yield Drawn(f"the {kind}", ElementTree.fromstring(sanitised_svg(markup)))
    for path, node in _svg_nodes(spec, ""):
        yield Drawn(f"the {kind}'s drawing at {path}", node_element(node))


def _svg_nodes(value: Any, path: str) -> Iterator[tuple[str, Mapping[str, Any]]]:
    if isinstance(value, Mapping):
        for key, item in value.items():
            if key in (THEMES_KEY, SVG_KEY) or ICON_KEY.search(key):
                continue
            where = f"{path}.{key}" if path else key
            if isinstance(item, Mapping) and _drawing(key, item):
                yield where, item
            else:
                yield from _svg_nodes(item, where)
    elif isinstance(value, list):
        for at, item in enumerate(value):
            if isinstance(item, Mapping) and item.get("tag") == SVG_TAG:
                yield f"{path}[{at}]", item
            else:
                yield from _svg_nodes(item, f"{path}[{at}]")


def _drawing(key: str, node: Mapping[str, Any]) -> bool:
    tag = node.get("tag")
    return tag == SVG_TAG or (key == DRAWING_KEY and tag in SVG_TAGS)


def _shapes(element: ElementTree.Element, inherited: Paints) -> Iterator[Shape]:
    tag = local_name(element.tag)
    if tag in DEFINITIONS:
        return
    paints = {**inherited, **_own_paints(element)}
    if tag in SHAPE_TAGS:
        yield Shape(element, paints)
    for child in element:
        yield from _shapes(child, paints)


def _own_paints(element: ElementTree.Element) -> dict[str, str]:
    found = {name: value for name, value in element.attrib.items() if name in PAINTS}
    for name, value in css_declarations(element.get("style") or ""):
        if name in PAINTS:
            found[name] = value
    return found


def _type_problems(drawn: Drawn) -> list[str]:
    box = svg_view_box(drawn.root.get("viewBox"))
    if box is None or box[2] <= 0:
        return []
    width = box[2]
    found: list[str] = []
    for words, units in drawn_texts(drawn.root):
        drawn_px = units * DRAWN_WIDTH_MIN / width
        if drawn_px + SIZE_TOLERANCE_PX < TEXT_FLOOR_PX or _on_scale(drawn_px):
            continue
        sizes = ", ".join(f"{size * width / DRAWN_WIDTH_MIN:g}" for size in UI_SIZES_PX)
        found.append(
            f"{drawn.where}: the text '{words}' is drawn at {drawn_px:.1f} px when the drawing is "
            f"{DRAWN_WIDTH_MIN} px wide, off the type scale; set it at {sizes} units (the scale's "
            f"{_listed(UI_SIZES_PX)} px), or give the words as a unit, as the kit's labels are"
        )
    return found


def _on_scale(drawn_px: float) -> bool:
    return any(abs(drawn_px - size) <= SIZE_TOLERANCE_PX for size in UI_SIZES_PX)


def _structure_problems(drawn: Drawn, shapes: Sequence[Shape], kind: str) -> list[str]:
    pointer = KIT_POINTER if kind in KIT_FIGURE_KINDS else AT_THE_BAR
    found: list[str] = []
    if len(shapes) < SHAPES_MIN:
        found.append(
            f"{drawn.where} draws {len(shapes)} shapes, fewer than the {SHAPES_MIN} a figure at the bar is "
            f"drawn with; {pointer}"
        )
    if not any(_inked(shape.paints) for shape in shapes):
        found.append(
            f"{drawn.where} has no line work in ink: edge what it shows in --ink-1, --ink-2 or --ink-3; {pointer}"
        )
    return found


def _inked(paints: Paints) -> bool:
    stroke = " ".join(paints.get("stroke", "").split())
    if stroke.casefold() == CURRENT_COLOUR:
        return True
    return bool(set(paint_roles(stroke)) & INK_ROLES)


def _kit_problems(drawn: Drawn, shapes: Sequence[Shape], words: str) -> list[str]:
    found: list[str] = []
    painted = sorted({role for shape in shapes for role in _materials(shape)})
    if painted:
        materials = ", ".join(f"--{role}" for role in painted)
        found.append(
            f"{drawn.where} paints {materials} by hand, which {_material_parts(words)} draws textured, framed "
            f"and named in a key; {KIT_POINTER}"
        )
    for part, word in parts_named_by(words):
        found.append(
            f"{drawn.where} is said to show {word}, which the kit's {part} part draws; {KIT_POINTER}"
        )
    return found


def _texture_problems(drawn: Drawn, shapes: Sequence[Shape]) -> list[str]:
    patterns = {element.get("id") for element in drawn.root.iter() if local_name(element.tag) == "pattern"}
    return [
        f"{drawn.where} paints --{role} on its <{local_name(shape.element.tag)}> with no texture: lay an in-drawing "
        f"<pattern> over the same shape, as the kit's {_listed(MATERIAL_PARTS)} parts do"
        for shape in shapes
        for role in _materials(shape)
        if not _textured(shape, shapes, patterns)
    ]


def _materials(shape: Shape) -> list[str]:
    return [role for role in paint_roles(shape.paints.get("fill", "")) if role in MATERIAL_ROLES]


def _textured(shape: Shape, shapes: Sequence[Shape], patterns: set[str | None]) -> bool:
    outline = _geometry(shape.element)
    return any(
        other.element is not shape.element
        and _geometry(other.element) == outline
        and _patterned(other, patterns)
        for other in shapes
    )


def _patterned(shape: Shape, patterns: set[str | None]) -> bool:
    found = LOCAL_URL.match(" ".join(shape.paints.get("fill", "").split()))
    return found is not None and found.group(1) in patterns


def _geometry(element: ElementTree.Element) -> tuple[str, ...]:
    return (local_name(element.tag), *(" ".join((element.get(name) or "").split()) for name in GEOMETRY))


def _words(root: ElementTree.Element, spec: Mapping[str, Any], texts: Mapping[str, str]) -> str:
    said = [element.text or "" for element in root.iter() if local_name(element.tag) in WORDED]
    said += [element.get("aria-label") or "" for element in root.iter()]
    head = spec.get("head")
    refs = [head.get("title") if isinstance(head, Mapping) else None, spec.get("alt")]
    said += [texts.get(ref, "") for ref in refs if isinstance(ref, str)]
    return " ".join(said)


def _material_parts(words: str) -> str:
    named = [part for part, _ in parts_named_by(words) if part in MATERIAL_PARTS]
    return f"the kit's {named[0]} part" if named else f"the kit's {_listed(MATERIAL_PARTS)} part"


def _listed(names: Sequence[object]) -> str:
    said = [str(name) for name in names]
    return said[0] if len(said) == 1 else f"{', '.join(said[:-1])} or {said[-1]}"
