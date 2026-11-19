from __future__ import annotations

import html
import re
from collections.abc import Iterator
from dataclasses import dataclass, field

from app.core.errors import InvalidInput

__all__ = ["Element", "Node", "anchored", "find_anchor", "parse_fragment"]

VOID_TAGS = frozenset(
    {
        "area",
        "base",
        "br",
        "col",
        "embed",
        "hr",
        "img",
        "input",
        "link",
        "meta",
        "param",
        "source",
        "track",
        "wbr",
    }
)
RAW_TEXT_TAGS = frozenset({"style", "script"})
TAG = re.compile(
    r"<(/?)([A-Za-z][\w:-]*)((?:\s+[^\s=/>]+(?:\s*=\s*(?:\"[^\"]*\"|'[^']*'|[^\s>]+))?)*)\s*(/?)>"
)
ATTRIBUTE = re.compile(r"([^\s=/>]+)(?:\s*=\s*(?:\"([^\"]*)\"|'([^']*)'|([^\s>]+)))?")
ID_ANCHOR = re.compile(r"#([\w-]+)")
ATTRIBUTE_ANCHOR = re.compile(r'\[([\w-]+)="([^"]*)"\]')


@dataclass
class Element:
    tag: str
    attrs: dict[str, str]
    children: list[Node] = field(default_factory=list)

    @property
    def elements(self) -> list[Element]:
        return [child for child in self.children if isinstance(child, Element)]

    @property
    def classes(self) -> list[str]:
        return self.attrs.get("class", "").split()

    def has_class(self, name: str) -> bool:
        return name in self.classes

    def walk(self) -> Iterator[Element]:
        yield self
        for child in self.elements:
            yield from child.walk()

    def text(self) -> str:
        return "".join(child if isinstance(child, str) else child.text() for child in self.children)


Node = Element | str


def parse_fragment(markup: str) -> Element:
    root = Element("#root", {})
    stack = [root]
    position = 0
    while position < len(markup):
        found = TAG.search(markup, position)
        end = found.start() if found else len(markup)
        if end > position:
            stack[-1].children.append(html.unescape(markup[position:end]))
        if found is None:
            break
        position = _take_tag(found, markup, stack)
    if len(stack) != 1:
        raise InvalidInput(f"unclosed element <{stack[-1].tag}> in the template")
    return root


def find_anchor(root: Element, anchor: str) -> Element:
    found = anchored(root, anchor)
    if len(found) != 1:
        raise InvalidInput(f"anchor {anchor} matches {len(found)} elements, not exactly one")
    return found[0]


def anchored(root: Element, anchor: str) -> list[Element]:
    test = _anchor_test(anchor)
    return [element for element in root.walk() if element is not root and test(element)]


def _take_tag(found: re.Match[str], markup: str, stack: list[Element]) -> int:
    closing, tag, raw_attrs, self_closing = found.groups()
    if closing:
        _close(stack, tag)
        return found.end()
    element = Element(tag, _attributes(raw_attrs))
    stack[-1].children.append(element)
    if tag.lower() in RAW_TEXT_TAGS:
        stop = markup.index(f"</{tag}>", found.end())
        element.children.append(markup[found.end() : stop])
        return stop + len(f"</{tag}>")
    if not self_closing and tag.lower() not in VOID_TAGS:
        stack.append(element)
    return found.end()


def _close(stack: list[Element], tag: str) -> None:
    if len(stack) < 2 or stack[-1].tag != tag:
        raise InvalidInput(f"</{tag}> closes <{stack[-1].tag}> in the template")
    stack.pop()


def _attributes(raw: str) -> dict[str, str]:
    attrs: dict[str, str] = {}
    for found in ATTRIBUTE.finditer(raw):
        name = found.group(1)
        value = next((group for group in found.groups()[1:] if group is not None), "")
        attrs[name] = html.unescape(value)
    return attrs


def _anchor_test(anchor: str):
    by_id = ID_ANCHOR.fullmatch(anchor)
    if by_id:
        return lambda element: element.attrs.get("id") == by_id.group(1)
    by_attribute = ATTRIBUTE_ANCHOR.fullmatch(anchor)
    if by_attribute:
        name, value = by_attribute.groups()
        return lambda element: element.attrs.get(name) == value
    raise InvalidInput(f'anchor {anchor} is neither #id nor [attribute="value"]')
