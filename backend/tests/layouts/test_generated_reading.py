import dataclasses
from pathlib import Path
from typing import Any

from app.research.chapter_keys import CHAPTER_KEYS, CHAPTER_TITLES, kind_chapter
from app.research.component_specs import checked_spec
from app.research.component_specs_general_delivery import DeliveredComponent, DeliveredUnit
from app.research.monograph_document import MonographDocument
from app.research.page_layout import PageLayout
from app.services.monograph_generated_assembly import assembled_document
from app.services.monograph_generated_drawings import Drawings
from app.services.monograph_generated_parts import RegisteredComponent
from app.services.monograph_generated_reading import (
    ReadingRead,
    ask_next_placed,
    language_switch_placed,
)

from .generated_parts import ALUM, TEXT_ALUM, generated

ASK = "bagh-print/reading/ask-next"
LANGUAGES = "bagh-print/reading/page-languages"
STUDENT = "bagh-print/process/student-version"
QUESTIONS = ("How does alum fix the madder red?", "What does the Baghini river give the cloth?")
READ = ReadingRead(
    path="/crafts/Bagh-Print", craft_slug="Bagh-Print", questions=QUESTIONS, languages=("hi", "ur")
)


def drawn(tmp_path: Path, **changes: Any) -> MonographDocument:
    built = assembled_document(
        dataclasses.replace(generated(), pictures=(), **changes), Drawings(root=tmp_path)
    )
    assert built is not None
    return built


def chapter_refs(built: MonographDocument, chapter: str) -> list[tuple[str, str]]:
    return [(entry.kind, entry.ref) for entry in built.content.layout if entry.chapter == chapter]


def student_version() -> RegisteredComponent:
    delivered = DeliveredComponent(
        spec={
            "level": "teen",
            "summary": "The student version",
            "detail": "Open to read",
            "title": "u0001",
            "lede": "u0002",
        },
        units={
            "u0001": DeliveredUnit(text="Alum and the red, for a younger reader"),
            "u0002": DeliveredUnit(text=TEXT_ALUM, claim_ids=[ALUM]),
        },
    )
    return RegisteredComponent(
        label=STUDENT,
        kind="reading_level",
        title="Alum and the red, the student version",
        description="The page's chemistry in one cited paragraph for a younger reader.",
        field="PROCESS",
        fields=(),
        subjects=("craft:Bagh-Print",),
        monograph=None,
        anchor=None,
        delivered=delivered,
    )


def test_a_generated_page_has_reading_and_media_chapters_before_its_sources() -> None:
    assert CHAPTER_KEYS[-3:] == ("reading", "media", "sources")
    assert (CHAPTER_TITLES["reading"], CHAPTER_TITLES["media"]) == (
        "Reading tools",
        "Pictures, video and film",
    )
    assert [kind_chapter(kind, "glance") for kind in ("ask_next", "reading_level", "quiz", "film")] == [
        "reading",
        "reading",
        "reading",
        "media",
    ]
    assert kind_chapter("reaction_player", "chem") == "chem"


def test_ask_next_comes_from_the_page_s_questions_and_the_switch_links_its_languages() -> None:
    asked = ask_next_placed(READ, "Bagh-Print")
    switch = language_switch_placed(READ, "Bagh-Print")
    assert asked is not None and switch is not None
    assert (asked.label, asked.entry.kind, asked.entry.chapter) == (ASK, "ask_next", "reading")
    assert asked.spec == {"craft": "Bagh-Print", "action": "Ask", "questions": list(QUESTIONS)}
    checked_spec("ask_next", asked.spec)
    checked_spec("language_switch", switch.spec)
    options = [(o["lang"], o["name"], o["direction"], o["href"]) for o in switch.spec["options"]]
    assert options == [
        ("en", "English", "ltr", "/crafts/Bagh-Print"),
        ("hi", "हिन्दी", "ltr", "/crafts/Bagh-Print/hi"),
        ("ur", "اردو", "rtl", "/crafts/Bagh-Print/ur"),
    ]
    assert "english" not in switch.spec and switch.spec["panels"] == []


def test_the_reading_chapter_is_drawn_by_default_with_ask_next_and_the_page_s_languages(
    tmp_path: Path,
) -> None:
    built = drawn(tmp_path, reading=READ)
    assert chapter_refs(built, "reading") == [
        ("unit", "chapter-reading"),
        ("component", ASK),
        ("component", LANGUAGES),
    ]
    chapters = list(dict.fromkeys(entry.chapter for entry in built.content.layout))
    assert chapters.index("reading") < chapters.index("sources")
    assert built.content.units["chapter-reading"].nodes == ["Reading tools"]
    kinds = {entry.label: entry.kind for entry in built.content.components}
    assert (kinds[ASK], kinds[LANGUAGES]) == ("ask_next", "language_switch")


def test_a_page_without_questions_or_translations_draws_no_reading_tool(tmp_path: Path) -> None:
    built = drawn(tmp_path)
    assert chapter_refs(built, "reading") == []
    english_only = drawn(tmp_path, reading=dataclasses.replace(READ, languages=()))
    assert chapter_refs(english_only, "reading") == [("unit", "chapter-reading"), ("component", ASK)]
    category = ReadingRead(path="/categories/Textiles", languages=("hi",))
    assert ask_next_placed(category, "Textiles") is None
    switch = language_switch_placed(category, "Textiles")
    assert switch is not None and switch.entry.subjects == []


def test_a_delivered_student_version_stands_in_the_reading_chapter_unless_the_layout_moves_it(
    tmp_path: Path,
) -> None:
    built = drawn(tmp_path, components=(student_version(),))
    assert ("component", STUDENT) in chapter_refs(built, "reading")
    assert ("component", STUDENT) not in chapter_refs(built, "made")
    entry = {"ref": STUDENT, "chapter": "chem", "order": 1, "role": "FIGURE"}
    layout = PageLayout.model_validate(
        {"subjectKind": "craft", "subjectSlug": "Bagh-Print", "version": 2, "entries": [entry]}
    )
    moved = drawn(tmp_path, components=(student_version(),), layout=layout)
    assert ("component", STUDENT) in chapter_refs(moved, "chem")
    assert ("component", STUDENT) not in chapter_refs(moved, "reading")
