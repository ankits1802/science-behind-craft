import json
import uuid

import pytest

from app.core.errors import InvalidInput
from app.models.enums import DISCIPLINES
from app.research.coverage import CoverageSubject, Holdings, field_coverage
from app.research.knowledge_api import Fact
from app.research.page_brief import BRIEF_BYTES_MAX, LINE_CHARS, BriefInput, PageBrief, fact_line, page_brief
from app.research.page_layout import PageLayout
from app.research.page_report_drawable import HeldChange, HeldShapes

from .page_report_rules_fixtures import FIGURE, SLUG, page_document

NAME = "Test craft"
CITED = [{"sourceId": "s1", "quote": "Alum fixes the red.", "locator": "line 4"}]
LAYOUT = PageLayout.model_validate(
    {
        "subjectKind": "craft",
        "subjectSlug": SLUG,
        "version": 3,
        "entries": [{"ref": FIGURE, "chapter": "chem", "order": 1, "role": "FIGURE", "size": "WIDE"}],
    }
)
STAGES = HeldShapes(stages=(HeldChange("S01", "Harda", ("c21",)), HeldChange("S02", "Syahi", ("c22",))))
STAGES_LINE = (
    "made: 2 stages in order (Harda, Syahi) with no player stepping through them, stated by c21, c22; "
    "draw it as a stage_player you write, each stage a kit scene of what its facts name if it serves the reader"
)


def fact(number: int, field: str | None, text: str = "Alum fixes the madder red.") -> Fact:
    return Fact(
        id=uuid.UUID(int=number), text=text, level="PROVISIONAL", field=field, fields=[], citations=CITED
    )


def ids(brief: PageBrief) -> list[uuid.UUID]:
    return [line.id for group in brief.facts for line in group.facts]


def size(brief: PageBrief) -> int:
    dumped = brief.model_dump(mode="json", by_alias=True)
    return len(json.dumps(dumped, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))


def test_a_fact_line_is_its_text_on_one_line_cut_at_a_word_when_long() -> None:
    assert fact_line("  Alum   fixes\nthe red. ") == "Alum fixes the red."
    said = " ".join(["madder"] * 40)
    line = fact_line(said)
    assert line.endswith("…") and len(line) <= LINE_CHARS
    assert said.startswith(line[:-1]) and said[len(line) - 1] == " "


def test_the_brief_holds_the_story_the_chapters_their_figures_and_every_fact_once() -> None:
    facts = [fact(1, "CHEMISTRY"), fact(2, "PROCESS"), fact(3, "HISTORY"), fact(4, None)]
    given = BriefInput(NAME, SLUG, facts, document=page_document(), layout=LAYOUT, held=STAGES)
    brief = page_brief(given)
    assert brief.lede == ["Test craft is printed with alum and madder in Kachchh."]
    assert [chapter.chapter for chapter in brief.chapters] == ["glance", "made", "chem", "history"]
    chem = brief.chapters[2]
    assert (chem.title, chem.headings, chem.sentences, chem.pictures, chem.facts) == (
        "The chemistry",
        ["Chemistry"],
        4,
        0,
        1,
    )
    (figure,) = chem.figures
    assert (figure.label, figure.kind, figure.title, figure.role, figure.size) == (
        FIGURE,
        "fact_table",
        "Alum on cotton",
        "FIGURE",
        "WIDE",
    )
    assert brief.opportunities == [STAGES_LINE]
    assert brief.layout_version == 3
    assert [(group.chapter, [line.id.int for line in group.facts]) for group in brief.facts] == [
        ("glance", [4]),
        ("made", [2]),
        ("chem", [1]),
        ("history", [3]),
    ]
    assert (brief.facts_total, brief.facts_before, brief.cursor) == (4, 0, None)


def test_the_brief_names_each_field_s_standing_in_its_chapter() -> None:
    coverage = field_coverage(
        CoverageSubject("craft", SLUG, NAME),
        Holdings(
            filed={name: frozenset({"CHEMISTRY"}) for name in ("c1", "c2", "c3")},
            sources={"c1": frozenset({"s1"}), "c2": frozenset({"s1"}), "c3": frozenset({"s2"})},
        ),
        claims_min=3,
    )
    brief = page_brief(BriefInput(NAME, SLUG, [fact(1, "CHEMISTRY")], coverage=coverage))
    keys = [chapter.chapter for chapter in brief.chapters]
    assert keys == ["glance", "made", "chem", "why", "history", "market", "people"]
    chem = brief.chapters[2]
    assert [(f.field, f.claims, f.standing) for f in chem.fields] == [
        ("CHEMISTRY", 3, "COVERED"),
        ("PHYSICS", 0, "MISSING"),
        ("BOTANY", 0, "MISSING"),
    ]
    assert (chem.title, chem.headings, chem.figures, brief.lede) == (None, [], [], [])


def test_a_large_page_s_brief_stays_under_its_bound_and_its_cursor_never_repeats_a_fact() -> None:
    long_text = " ".join(["the madder bath turns the alum print red"] * 6)
    facts = [fact(n, DISCIPLINES[n % len(DISCIPLINES)], long_text) for n in range(1, 601)]
    given = BriefInput(NAME, SLUG, facts, document=page_document())
    pages = [page_brief(given)]
    while pages[-1].cursor is not None:
        pages.append(page_brief(given, pages[-1].cursor))
    sent = [fact_id for page in pages for fact_id in ids(page)]
    assert len(pages) > 1 and len(sent) == len(set(sent)) == 600
    assert all(size(page) <= BRIEF_BYTES_MAX for page in pages)
    assert [page.facts_before for page in pages] == [
        sum(len(ids(p)) for p in pages[:n]) for n in range(len(pages))
    ]
    assert pages[0].chapters and all(not page.chapters and not page.opportunities for page in pages[1:])
    assert all(page.facts_total == 600 for page in pages)


def test_a_cursor_is_refused_once_the_facts_change_or_when_nothing_is_left() -> None:
    long_text = " ".join(["alum"] * 40)
    facts = [fact(n, "CHEMISTRY", long_text) for n in range(1, 500)]
    first = page_brief(BriefInput(NAME, SLUG, facts))
    assert first.cursor is not None
    with pytest.raises(InvalidInput, match="changed since this cursor"):
        page_brief(BriefInput(NAME, SLUG, facts[:-1]), first.cursor)
    digest = first.cursor.split(":")[1]
    with pytest.raises(InvalidInput, match="no fact left"):
        page_brief(BriefInput(NAME, SLUG, facts), f"{len(facts)}:{digest}")
    second = page_brief(BriefInput(NAME, SLUG, facts), first.cursor)
    assert set(ids(first)).isdisjoint(ids(second))
