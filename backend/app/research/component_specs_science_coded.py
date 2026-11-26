from __future__ import annotations

import uuid
from collections.abc import Iterator, Sequence
from typing import Annotated, Literal, Self

from pydantic import AfterValidator, Field, model_validator
from pydantic.json_schema import SkipJsonSchema

from .base import absent, empty
from .coded_figure_code import CODE_MAX_BYTES, CodeAsk, code_problems, shown_number_problems
from .coded_figure_still import still_texts
from .component_specs_general import DrawingThemes, GeneralHead
from .component_specs_general_svg import DRAWING_MAX_CHARS, sanitised_svg
from .component_specs_science_parts import SpecModel, UnitRef
from .unit_ids import UNIT_REF

__all__ = [
    "CODED_LIBRARIES",
    "CODE_KEY_PATTERN",
    "CREDIT_MAX_CHARS",
    "FILMS_MAX",
    "FILM_PATTERN",
    "MAP_DISTRICTS_MAX",
    "MAP_LAYERS",
    "MAP_WATERS_MAX",
    "PROBLEMS_SHOWN",
    "TEXTS_MAX",
    "VALUES_MAX",
    "CodedFigureSpec",
    "CodedFilm",
    "CodedMap",
    "CodedText",
    "CodedValue",
]

CODE_KEY_PATTERN = r"^[a-z][a-z0-9_]{0,39}$"
FILM_PATTERN = r"^/monographs/[A-Za-z0-9][A-Za-z0-9._/-]*\.(mp4|webm)$"
CODED_LIBRARIES = ("d3", "three")
MAP_LAYERS = ("states", "districts", "rivers", "relief")
VALUES_MAX = 120
TEXTS_MAX = 120
FILMS_MAX = 4
CREDIT_MAX_CHARS = 200
ONE_SOURCE = (
    "a film is either a file the site serves (src) or a clip of the media store (clip), one of the two"
)
MAP_DISTRICTS_MAX = 30
MAP_WATERS_MAX = 6
PROBLEMS_SHOWN = 8

CodeKey = Annotated[str, Field(pattern=CODE_KEY_PATTERN)]
StillSvg = Annotated[str, Field(max_length=DRAWING_MAX_CHARS), AfterValidator(sanitised_svg)]


class CodedValue(SpecModel):
    key: CodeKey
    value: float = Field(allow_inf_nan=False)
    reading: UnitRef


class CodedText(SpecModel):
    key: CodeKey
    unit: UnitRef


class CodedFilm(SpecModel):
    key: CodeKey
    src: str | None = Field(default=None, pattern=FILM_PATTERN, max_length=300, exclude_if=absent)
    clip: uuid.UUID | None = Field(default=None, exclude_if=absent)
    credit: SkipJsonSchema[str | None] = Field(default=None, max_length=CREDIT_MAX_CHARS, exclude_if=absent)

    @model_validator(mode="after")
    def _one_source(self) -> Self:
        if (self.src is None) == (self.clip is None):
            raise ValueError(ONE_SOURCE)
        return self


class CodedMap(SpecModel):
    layers: list[Literal[*MAP_LAYERS]] = Field(default_factory=list, max_length=len(MAP_LAYERS))
    districts: list[int] = Field(default_factory=list, max_length=MAP_DISTRICTS_MAX)
    rivers: list[str] = Field(default_factory=list, max_length=MAP_WATERS_MAX, exclude_if=empty)
    dams: list[str] = Field(default_factory=list, max_length=MAP_WATERS_MAX, exclude_if=empty)


class CodedFigureSpec(SpecModel):
    head: GeneralHead
    alt: UnitRef
    code: str = Field(min_length=1, max_length=CODE_MAX_BYTES)
    values: list[CodedValue] = Field(default_factory=list, max_length=VALUES_MAX)
    texts: list[CodedText] = Field(default_factory=list, max_length=TEXTS_MAX)
    libraries: list[Literal[*CODED_LIBRARIES]] = Field(default_factory=list, max_length=len(CODED_LIBRARIES))
    map: CodedMap | None = Field(default=None, exclude_if=absent)
    films: list[CodedFilm] = Field(default_factory=list, max_length=FILMS_MAX)
    still: StillSvg | None = Field(default=None, exclude_if=absent)
    themes: SkipJsonSchema[DrawingThemes | None] = Field(default=None, exclude_if=absent)

    @model_validator(mode="after")
    def _states_only_its_facts_and_rests_still(self) -> Self:
        problems = [
            *_key_problems([value.key for value in self.values], "value"),
            *_key_problems([text.key for text in self.texts], "text"),
            *_key_problems([film.key for film in self.films], "film"),
            *_key_problems(list(self.libraries), "library"),
        ]
        problems += code_problems(self._ask())
        data = frozenset(abs(value.value) for value in self.values)
        for text in still_texts(self.still) if self.still is not None else []:
            problems += shown_number_problems(text, data)
        if problems:
            raise ValueError(_joined(list(dict.fromkeys(problems))))
        return self

    def _ask(self) -> CodeAsk:
        return CodeAsk(
            code=self.code,
            values={value.key: value.value for value in self.values},
            texts=[text.key for text in self.texts],
            films=[film.key for film in self.films],
            mapped=self.map is not None,
            still=self.still is not None,
        )


def _key_problems(keys: Sequence[str], kind: str) -> Iterator[str]:
    for key in sorted({key for key in keys if keys.count(key) > 1}):
        yield f"the {kind} {key!r} is given twice"
    for key in keys:
        if UNIT_REF.match(key):
            yield f"the {kind} key {key!r} is a unit id; a key is a word of the code's own"


def _joined(problems: Sequence[str]) -> str:
    shown = "; ".join(problems[:PROBLEMS_SHOWN])
    more = len(problems) - PROBLEMS_SHOWN
    return f"{shown}; and {more} more" if more > 0 else shown
