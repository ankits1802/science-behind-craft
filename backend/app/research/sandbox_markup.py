from __future__ import annotations

from dataclasses import dataclass
from html.parser import HTMLParser

__all__ = [
    "FORBIDDEN_ELEMENTS",
    "NAMESPACE_URIS",
    "NUMERIC_ATTRIBUTES",
    "RAW_TEXT_ELEMENTS",
    "TEXT_ATTRIBUTES",
    "URL_ATTRIBUTES",
    "SandboxMarkup",
    "SandboxProblem",
]

RAW_TEXT_ELEMENTS = ("script", "style")
FORBIDDEN_ELEMENTS = frozenset(
    {
        "applet",
        "audio",
        "base",
        "body",
        "embed",
        "fencedframe",
        "form",
        "frame",
        "frameset",
        "head",
        "html",
        "iframe",
        "link",
        "listing",
        "math",
        "meta",
        "noembed",
        "noframes",
        "noscript",
        "object",
        "plaintext",
        "portal",
        "source",
        "textarea",
        "title",
        "track",
        "video",
        "xmp",
    }
)
URL_ATTRIBUTES = frozenset(
    {
        "action",
        "archive",
        "background",
        "cite",
        "codebase",
        "data",
        "formaction",
        "href",
        "longdesc",
        "manifest",
        "ping",
        "poster",
        "src",
        "srcset",
        "usemap",
        "xlink:href",
    }
)
TEXT_ATTRIBUTES = frozenset(
    {
        "alt",
        "aria-description",
        "aria-label",
        "aria-placeholder",
        "aria-roledescription",
        "aria-valuetext",
        "label",
        "placeholder",
        "title",
    }
)
NUMERIC_ATTRIBUTES = frozenset(
    {
        "aria-valuemax",
        "aria-valuemin",
        "aria-valuenow",
        "high",
        "low",
        "max",
        "min",
        "optimum",
        "start",
        "step",
        "value",
    }
)
NAMESPACE_URIS = frozenset(
    {
        "http://www.w3.org/2000/svg",
        "http://www.w3.org/1999/xlink",
        "http://www.w3.org/1999/xhtml",
        "http://www.w3.org/1998/Math/MathML",
    }
)


@dataclass(frozen=True)
class SandboxProblem:
    rule: str
    detail: str


class SandboxMarkup(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.problems: list[SandboxProblem] = []
        self.scripts: list[str] = []
        self.styles: list[str] = []
        self.texts: list[str] = []
        self.numbers: list[str] = []
        self.urls: list[tuple[str, str]] = []
        self.values: list[str] = []
        self.ids: list[str] = []
        self._raw: str | None = None
        self._foreign = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in FORBIDDEN_ELEMENTS:
            self.problems.append(SandboxProblem("ELEMENT", f"<{tag}>"))
        if tag in RAW_TEXT_ELEMENTS:
            self._raw_element(tag, attrs)
        if tag == "svg":
            self._foreign += 1
        for name, value in attrs:
            self._attribute(name, value or "")

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.handle_starttag(tag, attrs)
        if tag in RAW_TEXT_ELEMENTS:
            self.problems.append(SandboxProblem("MARKUP", f"a self-closing <{tag}>"))
            self.set_cdata_mode(tag)
            return
        self.handle_endtag(tag)

    def handle_endtag(self, tag: str) -> None:
        if tag == self._raw:
            self._raw = None
        if tag == "svg" and self._foreign:
            self._foreign -= 1

    def handle_data(self, data: str) -> None:
        {"script": self.scripts, "style": self.styles}.get(self._raw or "", self.texts).append(data)

    def handle_comment(self, data: str) -> None:
        self.problems.append(SandboxProblem("MARKUP", "a comment"))

    def handle_decl(self, decl: str) -> None:
        self.problems.append(SandboxProblem("MARKUP", "a declaration"))

    def handle_pi(self, data: str) -> None:
        self.problems.append(SandboxProblem("MARKUP", "a processing instruction"))

    def unknown_decl(self, data: str) -> None:
        self.problems.append(SandboxProblem("MARKUP", "a CDATA section"))

    def _raw_element(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if self._foreign:
            self.problems.append(SandboxProblem("MARKUP", f"<{tag}> inside <svg>"))
        if tag == "script" and attrs:
            self.problems.append(SandboxProblem("MARKUP", "a script element with attributes"))
        self._raw = tag

    def _attribute(self, name: str, value: str) -> None:
        if name == "id":
            self.ids.append(value)
        if name.startswith("on"):
            self.scripts.append(value)
        elif name == "style":
            self.styles.append(value)
        elif name == "xmlns" or name.startswith("xmlns:"):
            if value not in NAMESPACE_URIS:
                self.problems.append(SandboxProblem("URL", f"namespace {value!r}"))
        elif name in TEXT_ATTRIBUTES:
            self.texts.append(value)
        else:
            self._loaded_attribute(name, value)

    def _loaded_attribute(self, name: str, value: str) -> None:
        if name in NUMERIC_ATTRIBUTES or name.startswith("data-"):
            self.numbers.append(value)
        if name in URL_ATTRIBUTES:
            self.urls.append((name, value))
        if name == "attributename" and (
            value.casefold() in URL_ATTRIBUTES or value.casefold().startswith("on")
        ):
            self.problems.append(SandboxProblem("URL", f"an animation of {value}"))
        self.values.append(value)
