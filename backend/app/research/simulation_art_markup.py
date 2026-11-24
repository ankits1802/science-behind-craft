from __future__ import annotations

from html.parser import HTMLParser
from types import MappingProxyType
from typing import Any

__all__ = ["SVG_CASES", "ArtMarkup"]

SVG_TAG = "svg"
STYLE_TAG = "style"
SCRIPT_TAG = "script"
IMAGE_ROLE = "img"
PAINT_ATTRIBUTES = frozenset({"fill", "stroke", "color", "stop-color", "flood-color", "lighting-color"})
SVG_CASES = MappingProxyType(
    {
        name.casefold(): name
        for name in (
            "viewBox",
            "preserveAspectRatio",
            "patternUnits",
            "patternContentUnits",
            "patternTransform",
            "gradientUnits",
            "gradientTransform",
            "clipPath",
            "clipPathUnits",
            "maskUnits",
            "maskContentUnits",
            "markerWidth",
            "markerHeight",
            "markerUnits",
            "refX",
            "refY",
            "linearGradient",
            "radialGradient",
            "textPath",
            "textLength",
            "lengthAdjust",
            "foreignObject",
        )
    }
)

Node = dict[str, Any]


class ArtMarkup(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.styles: list[str] = []
        self.scripts: list[str] = []
        self.paints: list[str] = []
        self.pictured: list[str] = []
        self.drawings: list[Node] = []
        self._open: list[Node] = []
        self._raw: str | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        given = {name: value or "" for name, value in attrs}
        self._attributes(given)
        if tag != SVG_TAG and not self._open and given.get("role") == IMAGE_ROLE and given.get("aria-label"):
            self.pictured.append(given["aria-label"])
        if tag in (STYLE_TAG, SCRIPT_TAG):
            self._raw = tag
            getattr(self, f"{tag}s").append("")
            return
        if tag == SVG_TAG or self._open:
            node: Node = {"tag": SVG_CASES.get(tag, tag), "attrs": _cased(given), "children": []}
            if self._open:
                self._open[-1]["children"].append(node)
            self._open.append(node)

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.handle_starttag(tag, attrs)
        self.handle_endtag(tag)

    def handle_endtag(self, tag: str) -> None:
        if tag == self._raw:
            self._raw = None
            return
        if not self._open or self._open[-1]["tag"] != SVG_CASES.get(tag, tag):
            return
        closed = self._open.pop()
        if not self._open:
            self.drawings.append(closed)

    def handle_data(self, data: str) -> None:
        if self._raw is not None:
            found = getattr(self, f"{self._raw}s")
            found[-1] += data
        elif self._open and data.strip():
            self._open[-1]["children"].append(data)

    def _attributes(self, given: dict[str, str]) -> None:
        for name, value in given.items():
            if name.startswith("on"):
                self.scripts.append(value)
            elif name == STYLE_TAG:
                self.styles.append(value)
            elif name in PAINT_ATTRIBUTES:
                self.paints.append(value)


def _cased(given: dict[str, str]) -> dict[str, str]:
    return {SVG_CASES.get(name, name): value for name, value in given.items()}
