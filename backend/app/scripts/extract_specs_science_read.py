from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from app.core.errors import InvalidInput
from app.research.component_specs_science_parts import SVG_TAGS

from .extract_specs_science_dom import Element, Node

__all__ = [
    "drawing",
    "expect",
    "held",
    "holds_unit",
    "kids",
    "one_of",
    "only",
    "rich",
    "slot",
    "slot_unit",
    "styled_unit",
    "text_of",
    "unit_of",
]

SLOT_TAG = "kv-slot"
CITATION_CLASS = "kcite"
RICH_TAGS = frozenset({"i", "b", "sub", "sup"})


def expect(element: Element, tag: str, *classes: str, **attrs: str) -> Element:
    if element.tag != tag or sorted(element.classes) != sorted(classes):
        raise InvalidInput(
            f"expected <{tag} class={' '.join(classes)!r}>, found <{element.tag} {element.attrs}>"
        )
    for name, value in attrs.items():
        if element.attrs.get(name.replace("_", "-")) != value:
            raise InvalidInput(f"<{element.tag}> lacks {name}={value!r}: {element.attrs}")
    return element


def kids(element: Element) -> list[Element]:
    stray = [child for child in element.children if isinstance(child, str) and child.strip()]
    if stray:
        raise InvalidInput(f"<{element.tag} {element.attrs}> holds loose text {stray[0][:60]!r}")
    return element.elements


def only(element: Element) -> Element:
    found = kids(element)
    if len(found) != 1:
        raise InvalidInput(f"<{element.tag} {element.attrs}> holds {len(found)} elements, not one")
    return found[0]


def one_of(found: list[Element]) -> Element:
    if len(found) != 1:
        raise InvalidInput(
            f"expected one element, found {[(element.tag, element.attrs) for element in found]}"
        )
    return found[0]


def slot(element: Element, nested: Mapping[int, str]) -> dict[str, str]:
    label = nested.get(id(element))
    if label is None:
        raise InvalidInput(f"<{element.tag} {element.attrs}> is no registered component")
    return {"component": label}


def holds_unit(part: Element) -> bool:
    return any(element.tag == SLOT_TAG for element in part.walk())


def held(part: Element) -> None:
    if not any(element.tag == "button" and element.has_class(CITATION_CLASS) for element in part.walk()):
        raise InvalidInput(f"<{part.tag} {part.attrs}> is left out but carries no cited sentence")
    return


def slot_unit(element: Element) -> str | None:
    if element.tag == SLOT_TAG:
        return element.attrs["unit"]
    found = element.elements
    if len(found) == 1 and found[0].tag == SLOT_TAG and not element.text().strip():
        return found[0].attrs["unit"]
    return None


def unit_of(element: Element) -> str:
    unit = slot_unit(element)
    if unit is None:
        raise InvalidInput(f"<{element.tag} {element.attrs}> holds no single text unit")
    return unit


def styled_unit(element: Element) -> dict[str, Any]:
    style = element.attrs.get("class")
    extra = set(element.attrs) - {"class"}
    if extra:
        raise InvalidInput(f"<{element.tag}> carries {sorted(extra)} beyond a style")
    return {"tag": element.tag, "unit": unit_of(element)} | ({"style": style} if style else {})


def text_of(element: Element) -> str:
    if element.elements:
        raise InvalidInput(f"<{element.tag} {element.attrs}> holds markup where plain text was expected")
    return element.text()


def rich(nodes: list[Node]) -> list[Any]:
    runs: list[Any] = []
    for node in nodes:
        if isinstance(node, str):
            runs.append(node)
        elif node.tag in RICH_TAGS and not node.attrs:
            runs.append({"text": text_of(node), "style": node.tag})
        else:
            raise InvalidInput(f"<{node.tag} {node.attrs}> is not a rich-text run")
    return [run for run in runs if run != ""]


def drawing(element: Element) -> dict[str, Any]:
    if element.tag not in SVG_TAGS:
        raise InvalidInput(f"<{element.tag}> is not a drawing element")
    node: dict[str, Any] = {"tag": element.tag}
    if element.attrs:
        node["attrs"] = dict(element.attrs)
    children = [
        child if isinstance(child, str) else drawing(child)
        for child in element.children
        if not _layout(child)
    ]
    if children:
        node["children"] = children
    return node


def _layout(node: Node) -> bool:
    return isinstance(node, str) and not node.strip() and "\n" in node
