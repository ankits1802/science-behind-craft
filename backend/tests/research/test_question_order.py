import pytest

from app.models.enums import DISCIPLINES
from app.research.sections import (
    DISCIPLINE_TITLES,
    FALLBACK_HEADINGS,
    asked_disciplines,
    fallback_heading,
    is_facet_label,
    question_order,
    section_specs,
)

UNDERSTOOD = ["PROCESS", "MATERIALS", "CHEMISTRY"]


@pytest.mark.parametrize(
    ("question", "craft", "expected"),
    [
        (
            "Which mordant fixes the red in Kutch Ajrakh block printing?",
            "Kutch Ajrakh",
            ["CHEMISTRY", "MATERIALS", "PROCESS"],
        ),
        (
            "कच्छ की अजरख छपाई में लाल रंग पक्का करने के लिए कौन सा मॉर्डेंट इस्तेमाल होता है?",
            "Kutch Ajrakh",
            ["CHEMISTRY", "MATERIALS", "PROCESS"],
        ),
        ("How is Kutch Ajrakh made?", "Kutch Ajrakh", ["PROCESS", "MATERIALS", "CHEMISTRY"]),
        ("What cotton does Kutch Ajrakh use?", "Kutch Ajrakh", ["MATERIALS", "CHEMISTRY", "PROCESS"]),
        ("Tell me about Kutch Ajrakh.", "Kutch Ajrakh", ["MATERIALS", "CHEMISTRY", "PROCESS"]),
    ],
)
def test_sections_answer_the_question_first_and_the_full_process_comes_last(
    question: str, craft: str, expected: list[str]
) -> None:
    assert question_order(UNDERSTOOD, question, craft) == expected


def test_words_of_the_craft_s_own_name_ask_nothing() -> None:
    question = "Why is Blue Pottery of Jaipur so fragile?"
    assert asked_disciplines(["CHEMISTRY", "MATERIALS"], question, "Blue Pottery of Jaipur") == []
    assert asked_disciplines(["CHEMISTRY", "MATERIALS"], question, None) == ["CHEMISTRY"]


def test_the_indigo_and_water_questions_lead_with_their_own_fields() -> None:
    fields = ["PROCESS", "GEOGRAPHY", "CHEMISTRY"]
    assert (
        question_order(fields, "How does indigo turn blue on Kutch Ajrakh cloth?", "Kutch Ajrakh")[0]
        == "CHEMISTRY"
    )
    assert (
        question_order(fields, "How does the water of Kachchh shape Kutch Ajrakh?", "Kutch Ajrakh")[0]
        == "GEOGRAPHY"
    )


def test_the_depth_keeps_the_fields_the_question_asks_about_then_the_most_important() -> None:
    fields = ["PROCESS", "HISTORY", "CLIMATE", "ECOLOGY", "CHEMISTRY"]
    specs = section_specs(fields, "BASIC", question="Why is the red so fast?", craft_name="Kutch Ajrakh")
    assert [s.discipline for s in specs] == ["CHEMISTRY", "HISTORY", "CLIMATE", "PROCESS"]
    assert [s.id for s in specs] == ["s1", "s2", "s3", "s4"]
    unasked = section_specs(
        fields, "BASIC", question="Tell me about Kutch Ajrakh.", craft_name="Kutch Ajrakh"
    )
    assert [s.discipline for s in unasked] == ["HISTORY", "CLIMATE", "ECOLOGY", "PROCESS"]


def test_a_question_asking_more_fields_than_the_depth_shows_keeps_the_most_important_of_them() -> None:
    fields = ["HISTORY", "PROCESS", "CLIMATE", "CHEMISTRY", "MATERIALS", "ECOLOGY"]
    question = "How is the red mordant made, step by step, and how do the climate, the cotton and its waste shape it?"
    specs = section_specs(fields, "BASIC", question=question, craft_name="Kutch Ajrakh")
    assert [s.discipline for s in specs] == ["PROCESS", "CLIMATE", "CHEMISTRY", "MATERIALS"]


@pytest.mark.parametrize("craft", ["Kutch Ajrakh", None, "A" * 200])
def test_no_fallback_heading_is_a_field_label(craft: str | None) -> None:
    assert set(FALLBACK_HEADINGS) == set(DISCIPLINES)
    for discipline in DISCIPLINES:
        heading = fallback_heading(discipline, craft)
        assert not is_facet_label(heading)
        assert len(heading) <= 120 and heading[0].isupper()


def test_field_labels_are_recognised_whatever_their_case_or_punctuation() -> None:
    for title in DISCIPLINE_TITLES.values():
        assert is_facet_label(title.upper() + ".")
    assert is_facet_label("Chemistry") and is_facet_label("the process")
    assert not is_facet_label("Green out of the vat, blue in the air")
    assert not is_facet_label("When the Suran ran dry")
