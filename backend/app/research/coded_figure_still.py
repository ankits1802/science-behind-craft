from __future__ import annotations

from collections.abc import Iterator, Mapping
from typing import Any
from xml.etree import ElementTree

from .component_specs_general_svg import sanitised_svg
from .drawing_rules import local_name
from .drawing_spec_rules import node_element
from .simulation_art_markup import ArtMarkup

__all__ = [
    "CODE_KEY",
    "STILL_KEY",
    "STILL_TAG",
    "TEXT_TAGS",
    "UNIT_ATTRIBUTE",
    "code_still",
    "served_still",
    "still_node",
    "still_problems",
    "still_texts",
    "worded_still",
]

CODE_KEY = "code"
STILL_KEY = "still"
STILL_TAG = "svg"
UNIT_ATTRIBUTE = "data-unit"
SVG_NAMESPACE = "http://www.w3.org/2000/svg"
TEXT_TAGS = frozenset({"text", "tspan"})
LINKED = {"xlink:href": "href"}
NO_SVG = (
    "the code draws no svg to cut its still from; send still, an svg of the figure at rest, which exports and "
    "the first paint draw"
)
MANY = (
    "the code draws {count} svg elements; send still, an svg of the figure at rest, or draw the figure as one "
    "svg, whose markup at rest is its still"
)


def code_still(code: str) -> str | None:
    drawings = _drawings(code)
    if len(drawings) != 1:
        return None
    try:
        return sanitised_svg(_markup(drawings[0]))
    except ValueError:
        return None


def served_still(spec: Mapping[str, Any]) -> str | None:
    given = spec.get(STILL_KEY)
    if isinstance(given, str):
        return given
    code = spec.get(CODE_KEY)
    return code_still(code) if isinstance(code, str) else None


def still_problems(code: str, *, given: bool) -> Iterator[str]:
    if given:
        return
    drawings = _drawings(code)
    if not drawings:
        yield NO_SVG
        return
    if len(drawings) > 1:
        yield MANY.format(count=len(drawings))
        return
    try:
        sanitised_svg(_markup(drawings[0]))
    except ValueError as wrong:
        yield f"the figure's svg cannot be its still: {wrong}"


def still_texts(markup: str) -> list[str]:
    root = ElementTree.fromstring(markup)
    return [" ".join("".join(element.itertext()).split()) for element in root.iter() if _texted(element)]


def still_node(markup: str) -> dict[str, Any]:
    return _node(ElementTree.fromstring(markup))


def worded_still(node: Mapping[str, Any], words: Mapping[str, str]) -> dict[str, Any]:
    attrs = node.get("attrs") or {}
    key = attrs.get(UNIT_ATTRIBUTE)
    if node.get("tag") in TEXT_TAGS and key in words:
        return {**node, "children": [words[key]]}
    children = node.get("children") or []
    return {**node, "children": [c if isinstance(c, str) else worded_still(c, words) for c in children]}


def _texted(element: ElementTree.Element) -> bool:
    return local_name(element.tag) == "text" and bool("".join(element.itertext()).strip())


def _drawings(code: str) -> list[dict[str, Any]]:
    markup = ArtMarkup()
    markup.feed(code)
    markup.close()
    return markup.drawings


def _markup(node: Mapping[str, Any]) -> str:
    root = node_element(_linked(node))
    root.set("xmlns", SVG_NAMESPACE)
    return ElementTree.tostring(root, encoding="unicode")


def _linked(node: Mapping[str, Any]) -> dict[str, Any]:
    attrs = {LINKED.get(name, name): value for name, value in (node.get("attrs") or {}).items()}
    kept = {name: value for name, value in attrs.items() if ":" not in name and name != "xmlns"}
    children = [child if isinstance(child, str) else _linked(child) for child in node.get("children") or []]
    return {**node, "attrs": kept, "children": children}


def _node(element: ElementTree.Element) -> dict[str, Any]:
    children: list[Any] = [element.text] if element.text and element.text.strip() else []
    for child in element:
        children.append(_node(child))
        if child.tail and child.tail.strip():
            children.append(child.tail)
    attrs = {local_name(name): value for name, value in element.attrib.items()}
    return {"tag": local_name(element.tag), "attrs": attrs, "children": children}
