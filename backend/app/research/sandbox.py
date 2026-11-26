from __future__ import annotations

import re
from collections.abc import Iterable, Iterator, Mapping

from .sandbox_markup import (
    FORBIDDEN_ELEMENTS,
    NAMESPACE_URIS,
    NUMERIC_ATTRIBUTES,
    TEXT_ATTRIBUTES,
    URL_ATTRIBUTES,
    SandboxMarkup,
    SandboxProblem,
)
from .sandbox_numbers import LAYOUT_CONSTANTS, code_number_problems, counter_problems, shown_number_problems

__all__ = [
    "FORBIDDEN_APIS",
    "FORBIDDEN_ELEMENTS",
    "LAYOUT_CONSTANTS",
    "NAMESPACE_URIS",
    "NUMERIC_ATTRIBUTES",
    "SANDBOX_ATTRIBUTE",
    "SANDBOX_CSP",
    "SANDBOX_DATA_ELEMENT_ID",
    "SANDBOX_MAX_BYTES",
    "SANDBOX_RULES",
    "TEXT_ATTRIBUTES",
    "URL_ATTRIBUTES",
    "SandboxProblem",
    "sandbox_problems",
    "sandbox_safety_problems",
]

SANDBOX_ATTRIBUTE = "allow-scripts"
SANDBOX_CSP = (
    "default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; img-src data:; webrtc 'block'"
)
SANDBOX_DATA_ELEMENT_ID = "kv-data"
SANDBOX_MAX_BYTES = 200 * 1024
SANDBOX_RULES = ("SIZE", "MARKUP", "ELEMENT", "API", "URL", "NUMBER")
FORBIDDEN_APIS = (
    "fetch",
    "XMLHttpRequest",
    "WebSocket",
    "WebTransport",
    "EventSource",
    "sendBeacon",
    "import",
    "importScripts",
    "eval",
    "Function",
    "Worker",
    "SharedWorker",
    "serviceWorker",
    "RTCPeerConnection",
    "webkitRTCPeerConnection",
    "RTCDataChannel",
    "cookie",
    "localStorage",
    "sessionStorage",
    "indexedDB",
    "caches",
    "postMessage",
    "location",
    "Reflect",
    "Proxy",
    "getOwnPropertyDescriptor",
    "getOwnPropertyDescriptors",
    "getOwnPropertyNames",
    "getPrototypeOf",
    "setPrototypeOf",
    "defineProperty",
    "defineProperties",
    "defaultView",
    "contentWindow",
    "contentDocument",
    "innerHTML",
    "outerHTML",
    "insertAdjacentHTML",
    "DOMParser",
    "createContextualFragment",
    "srcdoc",
    "__proto__",
)
NAVIGATION_NAMES = ("top", "parent", "frames", "opener")

RAW_DECLARATION = re.compile(r"<[!?]")
RAW_ELEMENT = re.compile(
    r"<\s*+/?\s*+(" + "|".join(sorted(FORBIDDEN_ELEMENTS)) + r")(?![\w-])", re.IGNORECASE
)
QUOTED_ELEMENT = re.compile(
    r"([\"'`])\s*+(" + "|".join(sorted(FORBIDDEN_ELEMENTS | {"script"})) + r")\s*+\1", re.IGNORECASE
)
IMAGE_TYPE = r"image/(?:png|jpeg|gif|webp|svg\+xml)[;,]"
FRAGMENT_TARGET = r"#[A-Za-z][\w:.-]*+"
FRAGMENT = re.compile(rf"^{FRAGMENT_TARGET}$")
DATA_IMAGE = re.compile(rf"^data:{IMAGE_TYPE}", re.IGNORECASE)
ALLOWED_URL = re.compile(rf"^(?:{FRAGMENT_TARGET}|data:{IMAGE_TYPE})", re.IGNORECASE)
MARKUP_SCHEME = re.compile(
    r"(?<![\w.+-])(?:javascript|vbscript|livescript|blob|file|ftp|https?|wss?|filesystem|about|chrome"
    rf"|data(?!:{IMAGE_TYPE}))\s*+:",
    re.IGNORECASE,
)
SCRIPT_SCHEME = re.compile(
    r"\b(?:https?|wss?|ftp|file|filesystem)\s*+:\s*+//|\b(?:javascript|vbscript)\s*+:"
    r"|\b(?:stuns?|turns?):(?!\s)"
    rf"|\bdata\s*+:\s*+(?!{IMAGE_TYPE})[a-z]++/[a-z0-9.+-]++",
    re.IGNORECASE,
)
CSS_URL = re.compile(r"url\(\s*+(?:\"([^\"]*+)\"|'([^']*+)'|([^\"'()\s]*+))\s*+\)", re.IGNORECASE)
CSS_URL_OPENING = re.compile(r"url\s*+\(", re.IGNORECASE)
CSS_LOADS = re.compile(r"@import|image-set\s*+\(", re.IGNORECASE)
SCRIPT_ESCAPE = re.compile(r"\\u\{([0-9a-fA-F]{1,6})\}|\\u([0-9a-fA-F]{4})|\\x([0-9a-fA-F]{2})")
CSS_STRING = re.compile(r"\"(?:[^\"\\]|\\.)*+\"|'(?:[^'\\]|\\.)*+'", re.DOTALL)
MAX_CODE_POINT = 0x10FFFF
IDENTIFIER_END = r"(?![\w$])"
GLOBAL_OBJECT = r"(?<![\w$.])(?:window|self|globalThis|document|this)"
API_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    *((name, re.compile(rf"(?<![\w$]){re.escape(name)}{IDENTIFIER_END}")) for name in FORBIDDEN_APIS),
    *((name, re.compile(rf"(?<![\w$.]){name}{IDENTIFIER_END}")) for name in NAVIGATION_NAMES),
    (
        "window navigation",
        re.compile(rf"{GLOBAL_OBJECT}\s*+\.\s*+(?:{'|'.join(NAVIGATION_NAMES)}){IDENTIFIER_END}"),
    ),
    ("global as a value", re.compile(r"(?<![\w$])(?:window|self|globalThis)(?!\s*+\.\s*+[A-Za-z_$])")),
    ("this as a value", re.compile(r"(?<![\w$.])this\s*+(?:[),;\]}?:]|$)")),
    ("event view", re.compile(r"\.\s*+view(?![\w$])")),
    ("open", re.compile(r"(?<![\w$])open\s*+\(")),
    ("document.write", re.compile(r"\.\s*+write(?:ln)?\s*+\(")),
    ("string timer", re.compile(r"(?<![\w$])set(?:Timeout|Interval)\s*+\(\s*+[\"'`]")),
    (
        "computed global",
        re.compile(r"(?<![\w$.])(?:window|self|globalThis|document|navigator|frames|top|parent|this)\s*+\["),
    ),
    ("constructor", re.compile(rf"\.\s*+constructor{IDENTIFIER_END}|\[\s*+[\"'`]constructor")),
    ("with", re.compile(r"(?<![\w$.])with\s*+\(")),
)


def sandbox_problems(html: str, values: Mapping[str, float]) -> list[SandboxProblem]:
    return _problems(html, frozenset(abs(float(value)) for value in values.values()))


def sandbox_safety_problems(html: str) -> list[SandboxProblem]:
    return _problems(html, None)


def _problems(html: str, data: frozenset[float] | None) -> list[SandboxProblem]:
    if len(html.encode("utf-8")) > SANDBOX_MAX_BYTES:
        return [SandboxProblem("SIZE", f"larger than {SANDBOX_MAX_BYTES} bytes")]
    markup = SandboxMarkup()
    markup.feed(html)
    markup.close()
    problems = [
        *markup.problems,
        *_data_element_problems(markup.ids),
        *_raw_problems(html),
        *_script_problems(markup.scripts, data),
        *_style_problems(markup.styles),
        *_attribute_problems(markup),
        *(_number_problems(markup, data) if data is not None else ()),
    ]
    return list(dict.fromkeys(problems))


def _data_element_problems(ids: Iterable[str]) -> Iterator[SandboxProblem]:
    if SANDBOX_DATA_ELEMENT_ID in ids:
        yield SandboxProblem("MARKUP", f"an element with id {SANDBOX_DATA_ELEMENT_ID}")


def _raw_problems(html: str) -> Iterator[SandboxProblem]:
    if RAW_DECLARATION.search(html):
        yield SandboxProblem("MARKUP", "a comment or declaration")
    for match in RAW_ELEMENT.finditer(html):
        yield SandboxProblem("ELEMENT", f"<{match.group(1).casefold()}>")


def _script_problems(scripts: Iterable[str], data: frozenset[float] | None) -> Iterator[SandboxProblem]:
    for script in scripts:
        code = _without_namespaces(script)
        for name, pattern in API_PATTERNS:
            if pattern.search(code):
                yield SandboxProblem("API", name)
        for match in QUOTED_ELEMENT.finditer(code):
            yield SandboxProblem("ELEMENT", f"<{match.group(2).casefold()}>")
        for match in SCRIPT_SCHEME.finditer(code):
            yield SandboxProblem("URL", match.group(0))
        if data is not None:
            yield from code_number_problems(code, data)


def _without_namespaces(script: str) -> str:
    script = SCRIPT_ESCAPE.sub(_escaped_character, script)
    for uri in NAMESPACE_URIS:
        script = script.replace(uri, " ")
    return script


def _escaped_character(match: re.Match[str]) -> str:
    code = int(next(group for group in match.groups() if group is not None), 16)
    return chr(code) if code <= MAX_CODE_POINT else ""


def _style_problems(styles: Iterable[str]) -> Iterator[SandboxProblem]:
    for style in styles:
        for match in CSS_LOADS.finditer(style):
            yield SandboxProblem("URL", match.group(0))
        yield from _css_url_problems(style)


def _attribute_problems(markup: SandboxMarkup) -> Iterator[SandboxProblem]:
    for name, value in markup.urls:
        if not ALLOWED_URL.match(value.strip()):
            yield SandboxProblem("URL", f"{name}={value!r}")
    for value in markup.values:
        yield from _css_url_problems(value)


def _css_url_problems(text: str) -> Iterator[SandboxProblem]:
    for match in CSS_URL.finditer(text):
        target = next((group for group in match.groups() if group is not None), "").strip()
        if not (FRAGMENT.match(target) or DATA_IMAGE.match(target)):
            yield SandboxProblem("URL", f"url({target})")
    rest = CSS_URL.sub("", text)
    if CSS_URL_OPENING.search(rest):
        yield SandboxProblem("URL", "a url( that does not close")
    for match in MARKUP_SCHEME.finditer(rest):
        yield SandboxProblem("URL", match.group(0))


def _number_problems(markup: SandboxMarkup, data: frozenset[float]) -> Iterator[SandboxProblem]:
    strings = (m.group(0) for s in markup.styles for m in CSS_STRING.finditer(CSS_URL.sub("", s)))
    yield from shown_number_problems([*markup.texts, *strings], data)
    yield from counter_problems(markup.styles, data)
    for value in markup.numbers:
        yield from code_number_problems(value, data)
