import base64
import json
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest

from app.research.design_read import (
    DRAWING_FAILED,
    NO_PICTURES,
    NO_REPORT,
    NOT_DRAWN,
    READ,
    SKIPPED,
    UNREADABLE,
    ModelReading,
    design_read_of,
    drawing_skip,
    picture_chapter,
    pictures_key,
)
from app.research.design_read_prompt import (
    DESIGN_ASK,
    DesignGuidance,
    DesignPicture,
    ajrakh_rhythm,
    design_request,
    skill_sections,
)
from app.research.page_render import DrawingReport, DrawnProblem, RenderedImage
from app.research.structured import schema_problems
from app.services.page_report import bar_content

REPLIES = Path(__file__).with_name("design_read_replies")
GUIDANCE = DesignGuidance(
    rubric="# The designer's critique\n\nAsk.", sections="## 1. Principles", rhythm="- made"
)


def recorded(name: str) -> dict[str, Any]:
    return json.loads((REPLIES / f"{name}.json").read_text(encoding="utf-8"))


def reading(fixture: dict[str, Any], cost: str = "0.21") -> ModelReading:
    return ModelReading(
        text=fixture["reply"], provider=fixture["provider"], model=fixture["model"], cost_usd=Decimal(cost)
    )


def image(name: str, data: bytes = b"\xff\xd8jpeg") -> RenderedImage:
    encoded = base64.b64encode(data).decode("ascii")
    return RenderedImage(name=name, caption=f"{name} as drawn", width=576, height=640, data=encoded)


def test_the_pictures_of_a_wall_of_text_chapter_get_a_note_naming_it() -> None:
    fixture = recorded("wall-of-text")
    read = design_read_of(reading(fixture), fixture["chapters"])
    assert read.state == READ and read.cost_usd == Decimal("0.21") and read.model == "claude-opus-5-5"
    made = [note for note in read.notes if note.chapter == "made"]
    assert len(made) == 1 and "wall of text" in made[0].problem.lower()
    assert made[0].where.startswith("The eight paragraphs") and "stage player" in made[0].fix
    assert [note.chapter for note in read.notes] == ["made", "chem"]
    assert read.verdict is not None and "wall of prose" in read.verdict


def test_a_well_set_page_gets_no_note_and_keeps_its_verdict() -> None:
    fixture = recorded("well-set")
    read = design_read_of(reading(fixture), fixture["chapters"])
    assert (read.state, read.notes, read.chapters) == (READ, [], ["opening", "made"])
    assert read.verdict == (
        "Every chapter sets its figures beside the prose that needs them, in the design's colours."
    )


@pytest.mark.parametrize("text", ["not json", '{"notes": "a string", "verdict": "x"}', "[1, 2]"])
def test_an_answer_off_its_shape_gives_no_notes_and_says_so_with_its_cost(text: str) -> None:
    read = design_read_of(ModelReading(text=text, provider="P", model="m", cost_usd=Decimal("0.1")), ["made"])
    assert (read.state, read.reason, read.notes, read.cost_usd) == (SKIPPED, UNREADABLE, [], Decimal("0.1"))


def test_long_notes_are_cut_and_never_fail_the_read() -> None:
    text = json.dumps(
        {"notes": [{"chapter": "made", "where": "w" * 400, "problem": "p", "fix": "f"}], "verdict": "v" * 500}
    )
    read = design_read_of(ModelReading(text=text, provider="P", model="m", cost_usd=Decimal(0)), ["made"])
    assert read.state == READ and len(read.notes[0].where) == 301 and read.notes[0].where.endswith("…")
    assert read.verdict is not None and len(read.verdict) == 401


def test_any_drawing_that_made_pictures_is_read_and_one_without_pictures_is_skipped() -> None:
    problem = DrawnProblem(width=390, label="page", problem="is 310px wider than the 390px screen")
    failed = DrawingReport(state="FAILED", widths=[390, 1440], problems=[problem], images=[])
    unmade = DrawingReport(state="UNMADE", widths=[], problems=[], images=[], reason="down")
    checked = DrawingReport(state="CHECKED", widths=[390, 1440], problems=[], images=[])
    assert drawing_skip(failed, [image("first-screen-390")]) is None
    assert drawing_skip(failed, []) == DRAWING_FAILED
    assert drawing_skip(unmade, []) == NOT_DRAWN
    assert drawing_skip(None, []) == NO_REPORT
    assert drawing_skip(checked, []) == NO_PICTURES
    assert drawing_skip(checked, [image("first-screen-390")]) is None


def test_the_pictures_key_changes_with_any_picture_its_name_or_its_order() -> None:
    first, chapter = image("first-screen-390"), image("chapter-made", b"\xff\xd8made")
    key = pictures_key([first, chapter])
    assert len(key) == 64 and key == pictures_key([first, chapter])
    assert key != pictures_key([chapter, first])
    assert key != pictures_key([first, image("chapter-made", b"\xff\xd8other")])
    assert key != pictures_key([first, image("chapter-chem", b"\xff\xd8made")])


def test_each_picture_is_set_under_its_chapter_and_the_schema_lists_only_those_chapters() -> None:
    images = [image("first-screen-390"), image("first-screen-1440"), image("chapter-made")]
    assert [picture_chapter(found.name) for found in images] == ["opening", "opening", "made"]
    request = design_request(images, GUIDANCE)
    assert request.chapters == ("opening", "made") and request.pictures == 3
    assert request.parts[0] == GUIDANCE.rubric and request.parts[-1] == DESIGN_ASK
    pictured = [part for part in request.parts if isinstance(part, DesignPicture)]
    assert [(part.chapter, part.mime, part.data) for part in pictured][2] == (
        "made",
        "image/jpeg",
        b"\xff\xd8jpeg",
    )
    note = request.schema["properties"]["notes"]["items"]
    assert note["properties"]["chapter"]["enum"] == ["opening", "made"]
    assert schema_problems(request.schema) == []


def test_the_design_sections_are_cut_between_their_headings_or_refused() -> None:
    text = "# Skill\n\n## 1. Principles\n\nOne.\n\n## 3. Colour\n\nThree.\n\n## 4. Space\n\nFour."
    assert skill_sections(text, "## 1. Principles", "## 4. ") == (
        "## 1. Principles\n\nOne.\n\n## 3. Colour\n\nThree."
    )
    with pytest.raises(ValueError, match="Principles"):
        skill_sections("# A skill without them", "## 1. Principles", "## 4. ")


def test_kutch_ajrakh_s_rhythm_alternates_its_prose_and_figures_chapter_by_chapter() -> None:
    content = bar_content()
    rhythm = ajrakh_rhythm(content)
    keys = list(dict.fromkeys(entry.chapter for entry in content.layout))
    lines = rhythm.splitlines()
    assert len(lines) == len(keys) and all(f"({key}):" in line for key, line in zip(keys, lines, strict=True))
    assert "blocks of text" in rhythm and ", then a " in rhythm
