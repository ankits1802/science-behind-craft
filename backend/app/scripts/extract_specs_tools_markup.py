import re
from collections.abc import Callable
from dataclasses import dataclass, field
from html.parser import HTMLParser
from typing import Any

from app.research.monograph_page import MARK_TAGS

VOID = frozenset(
    {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr"}
)
ANCHOR_ATTRIBUTE = re.compile(r'^\[([a-z-]+)="(.*)"\]$')


@dataclass
class Element:
    tag: str
    attrs: dict[str, str]
    children: list[Element | str] = field(default_factory=list)

    def classes(self) -> list[str]:
        return self.attrs.get("class", "").split()

    def all(self, test: Callable[[Element], bool]) -> list[Element]:
        found = [self] if test(self) else []
        for child in self.children:
            if isinstance(child, Element):
                found += child.all(test)
        return found

    def one(self, test: Callable[[Element], bool]) -> Element:
        found = self.all(test)
        if len(found) != 1:
            raise ValueError(f"expected one element under <{self.tag}>, found {len(found)}")
        return found[0]

    def text(self) -> str:
        return "".join(c if isinstance(c, str) else c.text() for c in self.children)

    def own_text(self) -> str:
        return "".join(c for c in self.children if isinstance(c, str))


class _TreeBuilder(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.root = Element("root", {})
        self.stack = [self.root]

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        element = Element(tag, {key: value or "" for key, value in attrs})
        self.stack[-1].children.append(element)
        if tag not in VOID:
            self.stack.append(element)

    def handle_endtag(self, tag: str) -> None:
        for depth in range(len(self.stack) - 1, 0, -1):
            if self.stack[depth].tag == tag:
                del self.stack[depth:]
                return

    def handle_data(self, data: str) -> None:
        self.stack[-1].children.append(data)


def parse_markup(markup: str) -> Element:
    builder = _TreeBuilder()
    builder.feed(markup)
    builder.close()
    return builder.root


def has_class(name: str) -> Callable[[Element], bool]:
    return lambda element: name in element.classes()


def has_attr(key: str, value: str | None = None) -> Callable[[Element], bool]:
    return lambda element: key in element.attrs and (value is None or element.attrs[key] == value)


def anchor_test(anchor: str) -> Callable[[Element], bool]:
    if anchor.startswith("#"):
        return has_attr("id", anchor[1:])
    found = ANCHOR_ATTRIBUTE.match(anchor)
    if found is None:
        raise ValueError(f"no anchor form {anchor!r}")
    return has_attr(found.group(1), found.group(2))


def slot_ref(element: Element) -> str:
    return element.one(lambda e: e.tag == "kv-slot" and "unit" in e.attrs).attrs["unit"]


def has_slot(element: Element) -> bool:
    return bool(element.all(lambda e: e.tag == "kv-slot"))


def inline_nodes(children: list[Element | str]) -> list[Any]:
    return [child if isinstance(child, str) else _mark(child) for child in children if child != ""]


def _mark(element: Element) -> dict[str, Any]:
    tag, classes = element.tag, element.classes()
    if tag == "span" and classes[:1] == ["s"]:
        return _sentence(element, classes[1:])
    if tag == "span" and classes == ["nw"]:
        return _cite(element)
    if tag == "span" and classes == ["kv-figref"]:
        return {"m": "figref", "ref": element.attrs["data-figref"], "c": inline_nodes(element.children)}
    if tag == "span":
        return {"m": "span", **_class(element), "c": inline_nodes(element.children)}
    if tag == "i":
        return {"m": "i", **({"role": classes[0]} if classes else {}), "c": inline_nodes(element.children)}
    if tag in MARK_TAGS and not element.attrs:
        return {"m": tag, "c": inline_nodes(element.children)}
    if tag == "a":
        return _link(element)
    raise ValueError(f"<{tag} class={classes}> is not an inline mark")


def _class(element: Element) -> dict[str, str]:
    return {"cls": element.attrs["class"]} if element.attrs.get("class") else {}


def _sentence(element: Element, extra: list[str]) -> dict[str, Any]:
    named = {"src": "data-src", "sid": "data-sid", "pair": "data-pair"}
    found = {key: element.attrs[attr] for key, attr in named.items() if attr in element.attrs}
    return {
        "m": "s",
        **({"cls": " ".join(extra)} if extra else {}),
        **found,
        "c": inline_nodes(element.children),
    }


def _cite(element: Element) -> dict[str, Any]:
    *words, button = element.children
    if not isinstance(button, Element) or "kcite" not in button.classes():
        raise ValueError("a citation cluster ends with its kcite button")
    return {
        "m": "cite",
        "key": button.attrs["data-c"],
        "g": button.attrs["data-g"].split(),
        "c": inline_nodes(words),
    }


def _link(element: Element) -> dict[str, Any]:
    if element.attrs.get("class"):
        return {
            "m": "link",
            "cls": element.attrs["class"],
            "href": element.attrs["href"],
            "c": inline_nodes(element.children),
        }
    named = {"rel": "rel", "target": "target", "ask": "data-ask", "lang": "lang"}
    found = {key: element.attrs[attr] for key, attr in named.items() if attr in element.attrs}
    return {"m": "link", "href": element.attrs["href"], **found, "c": inline_nodes(element.children)}


def text_of(root: Element, test: Callable[[Element], bool]) -> str:
    return root.one(test).text().strip()
