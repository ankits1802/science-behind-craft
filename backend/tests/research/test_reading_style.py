import inspect
from types import SimpleNamespace

import pytest

from app.composer import prompt
from app.composer.prompt import styled
from app.research.reading_style import (
    READING_STYLE_INSTRUCTIONS,
    STYLE_LIMIT,
    piece_style,
    reading_style_for,
    style_paragraph,
)

CHILD = (
    "Reader: a school student under 14. Use everyday words and short sentences of about 12 words, never more "
    "than 18. The first time a scientific word appears, say what it means in the same sentence. Tell the "
    "process as a story of what the artisan's hands and materials do, step by step, warmly and plainly."
)
TEEN = (
    "Reader: a secondary-school student aged 14 to 17. Use clear words and sentences of at most 22 words. "
    "Name each scientific term and explain it once in plain words. Tell the process as a chain of causes and "
    "effects, step by step."
)
UNDERGRADUATE = (
    "Reader: a college student aged 18 to 22. Use the field's terms, each explained briefly the first time, "
    "and sentences of at most 28 words. Connect each step to the reason it works."
)
LIMIT = (
    "This changes only the wording: state the same facts, figures and citations you would for any reader, and "
    "follow every source rule above."
)


@pytest.mark.parametrize(
    ("band", "style"),
    [("UNDER_14", "CHILD"), ("14_17", "TEEN"), ("18_22", "UNDERGRADUATE"), ("23_PLUS", None)],
)
def test_a_students_band_chooses_the_style(band: str, style: str | None) -> None:
    assert reading_style_for("STUDENT", SimpleNamespace(ageBand=band, gender="WOMAN")) == style


@pytest.mark.parametrize("role", ["ARTISAN", "RESEARCHER", "PROFESSOR", "ADMIN", "MASTER_ADMIN"])
def test_every_other_role_keeps_todays_prompts(role: str) -> None:
    assert reading_style_for(role, SimpleNamespace(ageBand="UNDER_14", gender="MAN")) is None


def test_a_student_without_a_profile_gets_no_guessed_style() -> None:
    assert reading_style_for("STUDENT", None) is None


def test_the_paragraphs_are_the_contracts_word_for_word() -> None:
    assert dict(READING_STYLE_INSTRUCTIONS) == {"CHILD": CHILD, "TEEN": TEEN, "UNDERGRADUATE": UNDERGRADUATE}
    assert STYLE_LIMIT == LIMIT
    assert style_paragraph("TEEN") == f"{TEEN} {LIMIT}"
    assert style_paragraph(None) is None


def test_styling_appends_the_paragraph_after_a_blank_line_or_leaves_the_prompt_byte_for_byte() -> None:
    base = prompt.LEDE_SYSTEM_PROMPT
    assert styled(base, None) is base
    assert styled(base, "CHILD") == f"{base}\n\n{CHILD} {LIMIT}"


def test_only_the_kinds_a_composer_writes_keep_a_style() -> None:
    assert piece_style("prose", "TEEN") == "TEEN"
    assert piece_style("process_ladder", "CHILD") == "CHILD"
    assert piece_style("reaction_player", "TEEN") is None
    assert piece_style("map_layer", "CHILD") is None


def test_no_prompt_builder_takes_or_emits_gender() -> None:
    assert "gender" not in inspect.getsource(prompt).lower()
    for function in (styled, style_paragraph, reading_style_for):
        assert not any("gender" in name.lower() for name in inspect.signature(function).parameters)
