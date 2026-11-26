from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Craft
from app.research.chapter_keys import READING_CHAPTER
from app.research.component_specs_tools import AskNextSpec, LanguageOption, LanguageSwitchSpec
from app.research.monograph_document import ENGLISH
from app.research.monograph_page import ComponentEntry
from app.research.open_work_translation_keys import TRANSLATION_LANGUAGES
from app.research.page_translations import SERVED_TRANSLATION_STATUSES
from app.research.vocabulary import ANSWER_LANGUAGE_SPECS, text_direction

from .craft_page_family import family_names, family_place, suggested_questions
from .monograph_generated_kin import KinRead, PlacingPage, page_label, place_kin
from .open_work_subjects import WorkSubject
from .page_layouts import page_path
from .page_text_index import covered_counts

__all__ = [
    "ASK_NEXT_TAIL",
    "LANGUAGES_TAIL",
    "ReadingRead",
    "ask_next_placed",
    "language_switch_placed",
    "place_page_tools",
    "subject_reading",
]

CRAFT = "craft"
READING_FIELD = "OVERVIEW"
QUESTIONS_MAX = 12
ASK_NEXT_TAIL = "reading/ask-next"
LANGUAGES_TAIL = "reading/page-languages"
ASK_NEXT = (
    "ask_next",
    "Ask next",
    "Questions that pick up where this page stops, each starting a new answer at the same depth.",
)
LANGUAGES = (
    "language_switch",
    "Read this page in",
    "The page in each language it reads in, each passage translated from its English sentence with its citations.",
)
ASK_ACTION = "Ask"


@dataclass(frozen=True)
class ReadingRead:
    path: str | None = None
    craft_slug: str | None = None
    questions: tuple[str, ...] = ()
    languages: tuple[str, ...] = ()


@dataclass(frozen=True)
class ToolPlaced:
    label: str
    entry: ComponentEntry
    spec: dict[str, Any]


async def subject_reading(session: AsyncSession, subject: WorkSubject, name: str) -> ReadingRead:
    counts = await covered_counts(session, [subject.slug], SERVED_TRANSLATION_STATUSES)
    languages = tuple(
        code for code in TRANSLATION_LANGUAGES if counts.get((subject.kind, subject.slug, code), 0) > 0
    )
    path = page_path(subject.kind, subject.slug)
    craft = await session.get(Craft, subject.id) if subject.kind == CRAFT else None
    if craft is None:
        return ReadingRead(path=path, languages=languages)
    category, kind = await family_names(session, craft) or (craft.category, None)
    asked = suggested_questions(family_place(category, kind), name, catch_all=bool(craft.isCatchAll))
    return ReadingRead(
        path=path, craft_slug=craft.slug, questions=tuple(asked[:QUESTIONS_MAX]), languages=languages
    )


def ask_next_placed(read: ReadingRead, slug: str) -> ToolPlaced | None:
    if read.craft_slug is None or not read.questions:
        return None
    spec = AskNextSpec(craft=read.craft_slug, action=ASK_ACTION, questions=list(read.questions))
    return _placed(read, (slug, ASK_NEXT_TAIL), ASK_NEXT, spec.model_dump(mode="json", by_alias=True))


def language_switch_placed(read: ReadingRead, slug: str) -> ToolPlaced | None:
    if read.path is None or not read.languages:
        return None
    english = LanguageOption(lang=ENGLISH, name="English", direction="ltr", status="English", href=read.path)
    others = [_option(code, read.path) for code in read.languages]
    spec = LanguageSwitchSpec(label=LANGUAGES[1], options=[english, *others])
    dumped = spec.model_dump(mode="json", by_alias=True, exclude_none=True)
    return _placed(read, (slug, LANGUAGES_TAIL), LANGUAGES, dumped)


def place_page_tools(
    reads: tuple[KinRead, ReadingRead], slug: str, page: PlacingPage, components: dict[str, list[str]]
) -> None:
    kin, reading = reads
    place_kin(kin, slug, page, components)
    for placed in (ask_next_placed(reading, slug), language_switch_placed(reading, slug)):
        if placed is None or placed.label in page.components:
            continue
        page.components[placed.label] = placed.entry
        page.specs[placed.label] = placed.spec
        components.setdefault(READING_CHAPTER, []).append(placed.label)


def _option(code: str, path: str) -> LanguageOption:
    spec = ANSWER_LANGUAGE_SPECS[code]
    return LanguageOption(
        lang=code, name=spec.autonym, direction=text_direction(code), status=spec.label, href=f"{path}/{code}"
    )


def _placed(
    read: ReadingRead, at: tuple[str, str], named: tuple[str, str, str], spec: dict[str, Any]
) -> ToolPlaced:
    kind, title, description = named
    label = page_label(*at)
    entry = ComponentEntry(
        label=label,
        chapter=READING_CHAPTER,
        anchor="#" + label.replace("/", "--"),
        kind=kind,
        title=title,
        description=description,
        field=READING_FIELD,
        fields=[READING_FIELD],
        subjects=[f"craft:{read.craft_slug}"] if read.craft_slug is not None else [],
    )
    return ToolPlaced(label, entry, spec)
