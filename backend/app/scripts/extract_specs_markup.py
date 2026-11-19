from __future__ import annotations

import re
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
from html.parser import HTMLParser

from app.core.errors import InvalidInput

__all__ = [
    "Element",
    "Node",
    "find_anchor",
    "has_classes",
    "is_tag",
    "parse_markup",
]

VOID_ELEMENTS = frozenset(
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
TAG_NAME = re.compile(r"<\s*([^\s/>]+)")
QUOTED_VALUE = re.compile(r""""[^"]*"|'[^']*'""")
ATTRIBUTE_NAME = re.compile(r"""\s([^\s"'>/=]+)(?=\s*=|\s|/?>|$)""")
ID_ANCHOR = re.compile(r"^#([A-Za-z0-9_:.-]+)$")
ATTRIBUTE_ANCHOR = re.compile(r'^\[([a-z-]+)="([^"]*)"\]$')


@dataclass
class Element:
    tag: str
    attrs: dict[str, str]
    children: list[Node] = field(default_factory=list)

    @property
    def name(self) -> str:
        return self.tag.lower()

    @property
    def classes(self) -> list[str]:
        return self.attrs.get("class", "").split()

    def has_class(self, name: str) -> bool:
        return name in self.classes

    def elements(self) -> list[Element]:
        return [child for child in self.children if isinstance(child, Element)]

    def walk(self) -> Iterator[Element]:
        yield self
        for child in self.elements():
            yield from child.walk()

    def first(self, test: Callable[[Element], bool]) -> Element:
        for found in self.walk():
            if found is not self and test(found):
                return found
        raise InvalidInput(f"<{self.tag} class={self.attrs.get('class')!r}> holds no such element")

    def all(self, test: Callable[[Element], bool]) -> list[Element]:
        return [found for found in self.walk() if found is not self and test(found)]

    def text(self) -> str:
        return "".join(child if isinstance(child, str) else child.text() for child in self.children)


Node = Element | str


class _TreeBuilder(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.root = Element("#document", {})
        self.open: list[Element] = [self.root]

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        element = self._element(attrs)
        self.open[-1].children.append(element)
        if tag not in VOID_ELEMENTS:
            self.open.append(element)

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.open[-1].children.append(self._element(attrs))

    def handle_endtag(self, tag: str) -> None:
        for depth in range(len(self.open) - 1, 0, -1):
            if self.open[depth].name == tag:
                del self.open[depth:]
                return

    def handle_data(self, data: str) -> None:
        self.open[-1].children.append(data)

    def _element(self, attrs: list[tuple[str, str | None]]) -> Element:
        raw = QUOTED_VALUE.sub('""', self.get_starttag_text() or "")
        tag = TAG_NAME.match(raw)
        cased = {name.lower(): name for name in ATTRIBUTE_NAME.findall(raw)}
        named = {cased.get(name, name): value or "" for name, value in attrs}
        return Element(tag.group(1) if tag else "", named)


def is_tag(name: str, *classes: str) -> Callable[[Element], bool]:
    return lambda element: element.name == name and all(element.has_class(cls) for cls in classes)


def has_classes(*classes: str) -> Callable[[Element], bool]:
    return lambda element: all(element.has_class(cls) for cls in classes)


def parse_markup(markup: str) -> Element:
    builder = _TreeBuilder()
    builder.feed(markup)
    builder.close()
    return builder.root


def find_anchor(root: Element, anchor: str) -> Element:
    test = _anchor_test(anchor)
    found = [element for element in root.walk() if element is not root and test(element)]
    if len(found) != 1:
        raise InvalidInput(f"The anchor {anchor} matches {len(found)} elements, not one")
    return found[0]


def _anchor_test(anchor: str) -> Callable[[Element], bool]:
    by_id = ID_ANCHOR.match(anchor)
    if by_id:
        return lambda element: element.attrs.get("id") == by_id.group(1)
    by_attribute = ATTRIBUTE_ANCHOR.match(anchor)
    if by_attribute:
        name, value = by_attribute.group(1), by_attribute.group(2)
        return lambda element: element.attrs.get(name) == value
    raise InvalidInput(f"No anchor form {anchor!r}")
