from __future__ import annotations

import re
from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass
from typing import Any
from xml.etree import ElementTree

from .art_kit import KIT_PARTS, parts_named_by
from .component_specs_general_svg import sanitised_svg, svg_view_box
from .component_specs_kit_scene import KIT_SCENE_KINDS
from .component_specs_science_parts import SVG_TAGS
from .drawing_roles import DRAWING_ROLES, INDIGO, MATERIAL_ROLES, MOLECULE_ROLE
from .drawing_rules import DRAWN_WIDTH_MIN, TEXT_FLOOR_PX, drawn_texts, local_name
from .drawing_spec_rules import SVG_KEY, THEMES_KEY, node_element
from .drawn_paints import DrawnPaints, Shape, drawn_paints

__all__ = [
    "KIT_FIGURE_KINDS",
    "KIT_POINTER",
    "MATERIAL_PARTS",
    "MOLECULE_KINDS",
    "SCENE_POINTER",
    "SHAPES_MIN",
    "SIZE_TOLERANCE_PX",
    "SWATCH_KINDS",
    "UI_SIZES_PX",
    "Drawn",
    "data_drawing_problems",
    "drawn_art_problems",
    "free_drawings",
    "scene_problems",
]

KIT_FIGURE_KINDS = frozenset({"drawing", "diagram"})
MOLECULE_KINDS = frozenset({"structure_diagram", "molecule_3d"})
SWATCH_KINDS = frozenset({"swatch_pair", "swatch_cards"})
UI_SIZES_PX = (12, 13, 14, 16)
SIZE_TOLERANCE_PX = 0.25
SHAPES_MIN = 6
WORDED = frozenset({"title", "desc"})
INK_ROLES = frozenset({"ink-1", "ink-2", "ink-3"})
STROKE = "stroke"
ICON_KEY = re.compile(r"icon$", re.IGNORECASE)
DRAWING_KEY = "drawing"
SVG_TAG = "svg"
MATERIAL_FIELDS = frozenset({"material", "liquor", "layers.material"})
MATERIAL_PARTS = tuple(name for name, part in KIT_PARTS.items() if MATERIAL_FIELDS & set(part.materials))
KIT_POINTER = (
    "compose the figure from the kit instead: a diagram with a head, a layout and panels whose named parts "
    "the site draws (kalavigyan://components/diagram.schema.json)"
)
SCENE_POINTER = (
    "give the scene as a kit scene instead: one to three named parts the site draws, each labelled by a unit "
    "citing its facts (kalavigyan://components/{kind}.schema.json)"
)


@dataclass(frozen=True)
class Drawn:
    where: str
    root: ElementTree.Element


def drawn_art_problems(kind: str, spec: Mapping[str, Any], texts: Mapping[str, str]) -> list[str]:
    if kind in KIT_SCENE_KINDS:
        return scene_problems(kind, spec, texts)
    if kind not in KIT_FIGURE_KINDS:
        return data_drawing_problems(kind, spec)
    found: list[str] = []
    for drawn in free_drawings(kind, spec):
        words = _words(drawn.root, spec, texts)
        found += _held_problems(drawn, drawn_paints(drawn.root), words, KIT_POINTER)
        found += _named_problems(drawn, words)
    return list(dict.fromkeys(found))


def scene_problems(kind: str, spec: Mapping[str, Any], texts: Mapping[str, str]) -> list[str]:
    if kind not in KIT_SCENE_KINDS:
        return []
    pointer = SCENE_POINTER.format(kind=kind)
    found: list[str] = []
    for drawn in free_drawings(kind, spec):
        found += _held_problems(drawn, drawn_paints(drawn.root), _words(drawn.root, {}, texts), pointer)
    return list(dict.fromkeys(found))


def data_drawing_problems(kind: str, spec: Mapping[str, Any]) -> list[str]:
    if kind in MOLECULE_KINDS or kind in SWATCH_KINDS:
        return []
    found: list[str] = []
    for drawn in free_drawings(kind, spec):
        found += _painted_problems(drawn, drawn_paints(drawn.root), "", KIT_POINTER)
    return list(dict.fromkeys(found))


def _held_problems(drawn: Drawn, art: DrawnPaints, words: str, pointer: str) -> list[str]:
    return [
        *_type_problems(drawn),
        *_structure_problems(drawn, art, pointer),
        *_painted_problems(drawn, art, words, pointer),
    ]


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


def _structure_problems(drawn: Drawn, art: DrawnPaints, pointer: str) -> list[str]:
    found: list[str] = []
    shapes = art.shapes
    if len(shapes) < SHAPES_MIN:
        found.append(
            f"{drawn.where} draws {len(shapes)} shapes, fewer than the {SHAPES_MIN} a figure at the bar is "
            f"drawn with; {pointer}"
        )
    if not any(_inked(art, shape) for shape in shapes):
        found.append(
            f"{drawn.where} has no line work in ink: edge what it shows in --ink-1, --ink-2 or --ink-3; {pointer}"
        )
    return found


def _inked(art: DrawnPaints, shape: Shape) -> bool:
    return bool(set(art.roles(shape.paints.get(STROKE, ""), shape.paints)) & INK_ROLES)


def _painted_problems(drawn: Drawn, art: DrawnPaints, words: str, pointer: str) -> list[str]:
    shown = set(art.shown_roles())
    found: list[str] = []
    painted = sorted(shown & MATERIAL_ROLES)
    if painted:
        materials = ", ".join(f"--{role}" for role in painted)
        found.append(
            f"{drawn.where} paints {materials} by hand, which {_material_parts(words)} draws textured, framed "
            f"and named in a key; {pointer}"
        )
    unresolved = sorted(role for role in shown if not _design_token(role))
    if unresolved:
        named = ", ".join(f"var(--{role})" for role in unresolved)
        found.append(
            f"{drawn.where} paints through {named}, which the drawing does not declare and the design does not "
            "define for a drawing; a variable from the page can hold a depicted material, so paint a design role "
            "or a variable the drawing declares from one"
        )
    return found


def _design_token(role: str) -> bool:
    return role in DRAWING_ROLES or bool(INDIGO.match(role) or MOLECULE_ROLE.match(role))


def _named_problems(drawn: Drawn, words: str) -> list[str]:
    return [
        f"{drawn.where} is said to show {word}, which the kit's {part} part draws; {KIT_POINTER}"
        for part, word in parts_named_by(words)
    ]


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
