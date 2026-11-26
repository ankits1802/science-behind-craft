from __future__ import annotations

import base64
from collections.abc import Sequence
from dataclasses import dataclass
from itertools import groupby
from typing import Any

from .design_read import picture_chapter
from .monograph_page import LayoutEntry, MonographContent
from .page_render import RENDERED_MIME, RenderedImage
from .structured import schema_object

__all__ = [
    "DESIGN_ASK",
    "DESIGN_FIRST_SECTION",
    "DESIGN_LAST_SECTION_BEFORE",
    "DESIGN_SYSTEM",
    "DesignGuidance",
    "DesignPicture",
    "DesignRequest",
    "ajrakh_rhythm",
    "design_request",
    "design_schema",
    "skill_sections",
]

DESIGN_FIRST_SECTION = "## 1. Principles"
DESIGN_LAST_SECTION_BEFORE = "## 4. "
TITLE_KEPT = 60
CUT = "…"
DESIGN_SYSTEM = (
    "You are a book designer reading pictures of one page of KalaVigyan, a site on the science behind India's "
    "crafts, before its author proposes it, for an author whose client cannot see the pictures. You are given "
    "the designer's rubric every author reads their own pictures by, the design system the page is built in "
    "(its principles, its non-negotiables and its colours by role in four themes), how Kutch Ajrakh's approved "
    "page sets its chapters as examples of the thinking, never as a template, and pictures of this page. Judge "
    "only what the pictures show. Your notes are feedback the author judges; they pass or fail nothing."
)
DESIGN_ASK = (
    "Write the critique of this page's pictures the rubric asks for, chapter by chapter: a note names its "
    "chapter by the key given with its picture, the figure or passage, what is wrong and what to do about it; "
    "a chapter that is well set gets no note. End with the verdict on the whole page."
)
DESIGN_HEAD = "# The design system\n\n{sections}"
AJRAKH_HEAD = (
    "# Kutch Ajrakh's chapters as set\n\n"
    "How the approved page alternates prose and figures, chapter by chapter, top to bottom: the thinking a "
    "page follows, never its counts or its kinds.\n\n{chapters}"
)
PICTURES_HEAD = "# This page's pictures\n\nEach picture follows its chapter key and caption."
PICTURE_LINE = "Picture {number}, chapter {chapter}: {caption}"
TEXT_RUN = "{count} blocks of text"
ONE_TEXT = "a block of text"


@dataclass(frozen=True)
class DesignGuidance:
    rubric: str
    sections: str
    rhythm: str


@dataclass(frozen=True)
class DesignPicture:
    chapter: str
    caption: str
    mime: str
    data: bytes


@dataclass(frozen=True)
class DesignRequest:
    system: str
    parts: tuple[str | DesignPicture, ...]
    chapters: tuple[str, ...]
    schema: dict[str, Any]

    @property
    def pictures(self) -> int:
        return sum(isinstance(part, DesignPicture) for part in self.parts)

    def texts(self) -> str:
        return "\n".join([self.system, *(part for part in self.parts if isinstance(part, str))])


def skill_sections(text: str, first: str, after: str) -> str:
    start = text.find(first)
    end = text.find(after, start + 1) if start >= 0 else -1
    if start < 0 or end < 0:
        raise ValueError(f"the text has no '{first}' section followed by '{after}'")
    return text[start:end].strip()


def ajrakh_rhythm(content: MonographContent) -> str:
    titles = {chapter.key: chapter.title for chapter in content.chapters}
    chapters: dict[str, list[LayoutEntry]] = {}
    for entry in content.layout:
        chapters.setdefault(entry.chapter, []).append(entry)
    return "\n".join(
        f"- {titles.get(key, key)} ({key}): {', then '.join(_runs(entries, content))}."
        for key, entries in chapters.items()
    )


def _runs(entries: Sequence[LayoutEntry], content: MonographContent) -> list[str]:
    kinds = {component.label: component for component in content.components}
    runs: list[str] = []
    for is_unit, run in groupby(entries, key=lambda entry: entry.kind == "unit"):
        items = list(run)
        if is_unit:
            runs.append(ONE_TEXT if len(items) == 1 else TEXT_RUN.format(count=len(items)))
            continue
        runs += [_figure(kinds[item.ref].kind, kinds[item.ref].title) for item in items if item.ref in kinds]
    return runs


def design_schema(chapters: Sequence[str]) -> dict[str, Any]:
    text = {"type": "string"}
    note = schema_object(
        chapter={"type": "string", "enum": list(chapters)}, where=text, problem=text, fix=text
    )
    return schema_object(notes={"type": "array", "items": note}, verdict=text)


def design_request(images: Sequence[RenderedImage], guidance: DesignGuidance) -> DesignRequest:
    chapters = tuple(dict.fromkeys(picture_chapter(image.name) for image in images))
    parts: list[str | DesignPicture] = [
        guidance.rubric,
        DESIGN_HEAD.format(sections=guidance.sections),
        AJRAKH_HEAD.format(chapters=guidance.rhythm),
        PICTURES_HEAD,
    ]
    for number, image in enumerate(images, start=1):
        chapter = picture_chapter(image.name)
        parts.append(PICTURE_LINE.format(number=number, chapter=chapter, caption=image.caption))
        parts.append(DesignPicture(chapter, image.caption, RENDERED_MIME, base64.b64decode(image.data)))
    parts.append(DESIGN_ASK)
    return DesignRequest(
        system=DESIGN_SYSTEM, parts=tuple(parts), chapters=chapters, schema=design_schema(chapters)
    )


def _figure(kind: str, title: str) -> str:
    words = " ".join(title.split())
    shown = words if len(words) <= TITLE_KEPT else words[:TITLE_KEPT].rstrip() + CUT
    return f"a {kind.replace('_', ' ')} ({shown})"
