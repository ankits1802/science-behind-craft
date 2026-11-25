from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

from .export_pictures import Picture
from .export_stills import Still

if TYPE_CHECKING:
    from .page_export_words import ExportWords

__all__ = [
    "ExportBlock",
    "ExportChapter",
    "ExportFigure",
    "ExportPicture",
    "ExportReference",
    "ExportText",
    "PageExport",
    "Role",
    "Run",
    "RunStyle",
    "plain_runs",
    "plain_text",
]

RunStyle = Literal["", "i", "b", "sub", "sup"]
Role = Literal["heading", "subheading", "body", "term", "item", "quote", "note", "credit"]
SUBSCRIPT = str.maketrans("0123456789+-=()", "₀₁₂₃₄₅₆₇₈₉₊₋₌₍₎")
SUPERSCRIPT = str.maketrans("0123456789+-=()", "⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻⁼⁽⁾")


@dataclass(frozen=True)
class Run:
    text: str
    style: RunStyle = ""
    lang: str | None = None


@dataclass(frozen=True)
class ExportText:
    runs: tuple[Run, ...]
    role: Role = "body"
    lang: str | None = None

    @property
    def plain(self) -> str:
        return plain_runs(self.runs)


@dataclass(frozen=True)
class ExportPicture:
    picture: Picture
    alt: str


@dataclass(frozen=True)
class ExportFigure:
    label: str
    kind: str
    title: str
    stills: tuple[Still, ...]
    lines: tuple[ExportText, ...]
    note: str | None = None
    credits: tuple[str, ...] = ()
    pictures: tuple[ExportPicture, ...] = ()
    note_lang: str | None = None


ExportBlock = ExportText | ExportFigure


@dataclass(frozen=True)
class ExportChapter:
    key: str
    title: str | None
    blocks: tuple[ExportBlock, ...]


@dataclass(frozen=True)
class ExportReference:
    number: int
    text: str
    url: str | None


@dataclass(frozen=True)
class PageExport:
    title: str
    language: str
    page_url: str
    version: int
    reading_note: ExportText | None
    chapters: tuple[ExportChapter, ...]
    references: tuple[ExportReference, ...]
    words: ExportWords

    def figures(self) -> list[ExportFigure]:
        return [
            block for chapter in self.chapters for block in chapter.blocks if isinstance(block, ExportFigure)
        ]


def plain_runs(runs: tuple[Run, ...]) -> str:
    return "".join(_plain(run) for run in runs)


def plain_text(text: str, role: Role = "body") -> ExportText:
    return ExportText(runs=(Run(text),), role=role)


def _plain(run: Run) -> str:
    if run.style == "sub":
        return run.text.translate(SUBSCRIPT)
    if run.style == "sup":
        return run.text.translate(SUPERSCRIPT)
    return run.text
