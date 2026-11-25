from __future__ import annotations

import re
from collections.abc import Iterable, Iterator, Mapping, Sequence
from dataclasses import dataclass
from html.parser import HTMLParser
from types import MappingProxyType

from .coded_figure_still import STILL_TAG, UNIT_ATTRIBUTE, still_problems
from .quotes import numbers_in
from .sandbox import SANDBOX_DATA_ELEMENT_ID, sandbox_safety_problems
from .sandbox_markup import RAW_TEXT_ELEMENTS, TEXT_ATTRIBUTES, SandboxProblem
from .simulation_art import FRAME_FLAG, TIMERS
from .unit_labels import COUNTING_MAX, LABEL_MAX_CHARS

__all__ = [
    "CODED_FIGURE",
    "CODE_MAX_BYTES",
    "FILM_ATTRIBUTE",
    "MAP_ATTRIBUTE",
    "MAP_ELEMENT_ID",
    "UNIT_LABEL_ATTRIBUTE",
    "WORDS_ELEMENT_ID",
    "CodeAsk",
    "code_problems",
]

CODED_FIGURE = "coded_figure"
CODE_MAX_BYTES = 64 * 1024
WORDS_ELEMENT_ID = "kv-words"
MAP_ELEMENT_ID = "kv-map"
FILMS_ELEMENT_ID = "kv-films"
RESERVED_IDS = (WORDS_ELEMENT_ID, MAP_ELEMENT_ID, FILMS_ELEMENT_ID)
UNIT_LABEL_ATTRIBUTE = "data-unit-label"
FILM_ATTRIBUTE = "data-film"
MAP_ATTRIBUTE = "data-map"
SCRIPT_TAG = "script"
STYLE_TAG = "style"
VIDEO_ELEMENT = "<video>"
HANDLER_PREFIX = "on"
SHOWN_CHARS = 40
PROSE_WORDS_MIN = 2
SENTENCE_WORDS_MIN = 6
WORD = re.compile(r"[^\W\d_]{3,}")
SCRIPT_STRING = re.compile(r"\"(?:[^\"\\\n]|\\.)*\"|'(?:[^'\\\n]|\\.)*'|`(?:[^`\\]|\\.)*`")
TEMPLATE_HOLE = re.compile(r"\$\{[^}]*\}")
CSS_CONTENT = re.compile(r"(?<![\w-])content\s*:\s*([^;}]*)", re.IGNORECASE)
CSS_STRING = re.compile(r"\"([^\"]*)\"|'([^']*)'")
SANDBOX_WORDS: Mapping[str, str] = MappingProxyType(
    {
        "SIZE": "the code is {detail}",
        "MARKUP": "the code holds {detail}, which the frame refuses",
        "ELEMENT": "the code holds {detail}, which the frame refuses",
        "API": (
            "the code uses {detail}, which the frame refuses: a figure reaches no network, storage, cookie, "
            "other window or address, and its libraries are named in libraries"
        ),
        "URL": (
            "the code names {detail}, which the frame refuses: a figure loads nothing itself, and a film is "
            "named in films and shown by data-film"
        ),
    }
)
STILL_FLAG = (
    "the code times its motion without reading document.documentElement.dataset.reducedMotion, which the frame "
    "sets under either reduced-motion switch; read it and draw the last state at once, since under it no "
    "timer or animation frame runs"
)


@dataclass(frozen=True)
class CodeAsk:
    code: str
    values: Mapping[str, float]
    texts: Sequence[str]
    films: Sequence[str] = ()
    mapped: bool = False
    still: bool = False


class CodeMarkup(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.texts: list[str] = []
        self.shown: list[str] = []
        self.keys: list[tuple[str, str]] = []
        self.scripts: list[str] = []
        self.styles: list[str] = []
        self.ids: list[str] = []
        self.maps = 0
        self._raw: str | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        given = {name: value or "" for name, value in attrs}
        if tag in RAW_TEXT_ELEMENTS:
            self._raw = tag
            (self.scripts if tag == SCRIPT_TAG else self.styles).append("")
        if tag == STILL_TAG and MAP_ATTRIBUTE in given:
            self.maps += 1
        for name, value in given.items():
            self._attribute(name, value)

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.handle_starttag(tag, attrs)
        if tag == self._raw:
            self._raw = None

    def handle_endtag(self, tag: str) -> None:
        if tag == self._raw:
            self._raw = None

    def handle_data(self, data: str) -> None:
        if self._raw == SCRIPT_TAG:
            self.scripts[-1] += data
        elif self._raw == STYLE_TAG:
            self.styles[-1] += data
        elif data.strip():
            self.texts.append(" ".join(data.split()))

    def _attribute(self, name: str, value: str) -> None:
        if name == "id":
            self.ids.append(value)
        elif name in (UNIT_ATTRIBUTE, UNIT_LABEL_ATTRIBUTE, FILM_ATTRIBUTE):
            self.keys.append((name, value))
        elif name.startswith(HANDLER_PREFIX):
            self.scripts.append(value)
        elif name == STYLE_TAG:
            self.styles.append(value)
        elif name in TEXT_ATTRIBUTES and value.strip():
            self.shown.append(" ".join(value.split()))


def code_problems(ask: CodeAsk) -> list[str]:
    size = len(ask.code.encode("utf-8"))
    if size > CODE_MAX_BYTES:
        return [f"the code is {size} bytes, past the {CODE_MAX_BYTES} bytes a coded figure may hold"]
    markup = CodeMarkup()
    markup.feed(ask.code)
    markup.close()
    data = frozenset(abs(value) for value in ask.values.values())
    found = [
        *_sandbox_problems(ask),
        *_reserved_problems(markup),
        *_said_problems(_free_texts(markup), data),
        *_key_problems(markup, ask),
        *_rest_problems(markup, ask),
        *still_problems(ask.code, given=ask.still),
    ]
    return list(dict.fromkeys(found))


def _sandbox_problems(ask: CodeAsk) -> Iterator[str]:
    for problem in sandbox_safety_problems(ask.code):
        if ask.films and problem.rule == "ELEMENT" and problem.detail == VIDEO_ELEMENT:
            continue
        yield _sandboxed(problem)


def _sandboxed(problem: SandboxProblem) -> str:
    return SANDBOX_WORDS.get(problem.rule, "the code fails the frame's {detail}").format(
        detail=problem.detail
    )


def _reserved_problems(markup: CodeMarkup) -> Iterator[str]:
    for reserved in (SANDBOX_DATA_ELEMENT_ID, *RESERVED_IDS):
        if reserved in markup.ids:
            yield f"the code holds an element with id {reserved}, which the frame keeps for the figure's data"


def _free_texts(markup: CodeMarkup) -> Iterator[str]:
    yield from markup.texts
    yield from markup.shown
    for style in markup.styles:
        for content in CSS_CONTENT.finditer(style):
            for found in CSS_STRING.finditer(content.group(1)):
                said = found.group(1) if found.group(1) is not None else found.group(2)
                if said.strip():
                    yield said
    for script in markup.scripts:
        for literal in SCRIPT_STRING.finditer(script):
            said = TEMPLATE_HOLE.sub(" ", literal.group(0)[1:-1])
            if " " in said.strip() and len(WORD.findall(said)) >= PROSE_WORDS_MIN:
                yield " ".join(said.split())


def _said_problems(texts: Iterable[str], data: frozenset[float]) -> Iterator[str]:
    for text in texts:
        if len(text) > LABEL_MAX_CHARS and len(WORD.findall(text)) >= SENTENCE_WORDS_MIN:
            yield (
                f"the code states {text[:SHOWN_CHARS]!r}... in words of its own; a label is at most "
                f"{LABEL_MAX_CHARS} characters, and a fact in words is a unit in texts, shown by data-unit"
            )
        yield from shown_number_problems(text, data)


def shown_number_problems(text: str, data: frozenset[float]) -> Iterator[str]:
    for numeral in numbers_in(text):
        value = float(numeral)
        if value in data or (value.is_integer() and 0 <= value <= COUNTING_MAX):
            continue
        yield (
            f"the code shows {numeral} in {text[:SHOWN_CHARS]!r}, which is not one of its values; a number it "
            "states is a value in values, stated by its cited reading"
        )


def _key_problems(markup: CodeMarkup, ask: CodeAsk) -> Iterator[str]:
    held = {
        UNIT_ATTRIBUTE: set(ask.texts),
        UNIT_LABEL_ATTRIBUTE: set(ask.texts),
        FILM_ATTRIBUTE: set(ask.films),
    }
    for name, key in dict.fromkeys(markup.keys):
        if key not in held[name]:
            group = "films" if name == FILM_ATTRIBUTE else "texts"
            yield f"the code names {key!r} by {name}, which {group} does not hold"


def _rest_problems(markup: CodeMarkup, ask: CodeAsk) -> Iterator[str]:
    timed = any(TIMERS.search(script) for script in markup.scripts)
    if timed and not any(FRAME_FLAG.search(script) for script in markup.scripts):
        yield STILL_FLAG
    if ask.mapped and not markup.maps:
        yield (
            "the figure declares a map but holds no svg with data-map, into which the site draws its base and the "
            "Survey of India outline"
        )
