import json
from typing import Any

import pytest

from app.data.craft_families import (
    CRAFT_FAMILIES_FILE,
    FamilyPlace,
    load_craft_families,
    parse_craft_families,
)
from app.data.craft_master_loader import load_master
from app.services.craft_page_family import suggested_questions
from app.services.craft_page_records import page_craft
from app.services.curation_preview import master_craft

TEXTILES = "Textiles based Craft Category"
BLOCK_PRINTING = "Hand Block Printing"
PLURAL = "Farrukhabad Prints"
AGREEING = ("is", "are", "was", "were", "does", "do", "has", "have")


def raw() -> dict[str, Any]:
    return json.loads(CRAFT_FAMILIES_FILE.read_text(encoding="utf-8"))


def test_every_register_family_and_kind_has_one_editorial_entry() -> None:
    families = load_craft_families()
    master = load_master()
    assert {family.slug for family in families.families} == {craft.category_slug for craft in master}
    kinds = {kind.slug for family in families.families for kind in family.kinds}
    assert kinds == {craft.sub_category_slug for craft in master}
    assert (len(families.families), len(kinds)) == (9, 36)


def test_each_kind_sits_under_its_register_family() -> None:
    families = load_craft_families()
    for craft in load_master():
        family = families.family(craft.category_slug)
        assert family is not None
        assert craft.sub_category_slug in {kind.slug for kind in family.kinds}


def test_register_names_find_the_editorial_labels() -> None:
    place = load_craft_families().place_of(TEXTILES, BLOCK_PRINTING)
    assert place.family is not None and place.kind is not None
    assert (place.family.label, place.kind.label) == ("Textiles", "Hand block printing")
    assert place.kind.other_name == "Other hand block printing"


def test_an_unknown_kind_keeps_its_family_and_asks_the_default_questions() -> None:
    families = load_craft_families()
    place = families.place_of(TEXTILES, "Not a kind")
    assert place.family is not None and place.family.label == "Textiles"
    assert place.kind is None
    assert families.questions(place, "Tie and Dye") == [
        "Which materials go into Tie and Dye?",
        "What are the stages in the making of Tie and Dye?",
        "How did the tradition of Tie and Dye begin, and where does the work go on today?",
    ]


def test_questions_name_the_craft_once_each() -> None:
    families = load_craft_families()
    asked = families.questions(families.place_of(TEXTILES, BLOCK_PRINTING), "Kutch Ajrakh")
    assert asked == [
        "How do mordants and dyes fix the colours of Kutch Ajrakh in the cloth?",
        "What are the stages of Kutch Ajrakh, from plain cloth to finished print?",
        "What do local water and climate give to the colours of Kutch Ajrakh?",
    ]


def test_a_plural_name_reads_as_well_as_a_singular_one() -> None:
    families = load_craft_families()
    asked = families.questions(families.place_of(TEXTILES, BLOCK_PRINTING), PLURAL)
    assert asked == [
        "How do mordants and dyes fix the colours of Farrukhabad Prints in the cloth?",
        "What are the stages of Farrukhabad Prints, from plain cloth to finished print?",
        "What do local water and climate give to the colours of Farrukhabad Prints?",
    ]
    for family in families.families:
        for kind in family.kinds:
            for question in families.questions(FamilyPlace(family, kind), PLURAL):
                words = question.replace("?", "").replace(",", "").split()
                at = words.index("Farrukhabad")
                assert words[at - 1] not in AGREEING and words[at + 2 : at + 3] != ["is"], question
                assert not {"it", "its", "they", "their", "them"} & set(words), question


def test_a_catch_all_row_asks_its_kinds_own_questions() -> None:
    place = load_craft_families().place_of(TEXTILES, BLOCK_PRINTING)
    assert suggested_questions(place, "Other hand block printing", catch_all=True) == [
        "How do mordants and dyes fix the colours of a block print in the cloth?",
        "What are the stages of hand block printing, from plain cloth to finished print?",
        "Why do water and climate matter so much to hand block printing?",
    ]


def test_every_catch_all_row_is_named_and_asked_about_by_its_kind() -> None:
    families = load_craft_families()
    rows = [craft for craft in load_master() if craft.is_catch_all]
    assert len(rows) == 35
    for row in rows:
        craft, names = master_craft(row.slug)
        shown = page_craft(craft, names)
        kind = families.kind(row.sub_category_slug)
        assert kind is not None and shown.display_name == kind.other_name
        asked = suggested_questions(families.place_of(*names), shown.display_name, catch_all=True)
        assert asked == list(kind.other_questions)
        assert all(kind.other_name.casefold() not in question.casefold() for question in asked)


@pytest.mark.parametrize(
    ("change", "message"),
    [
        (lambda body: body.update(version=1), "version 1"),
        (lambda body: body["families"][0]["kinds"][0].update(questions=["Why {craft}?"]), "1 questions"),
        (
            lambda body: body["families"][0]["kinds"][0]["questions"].__setitem__(0, "Why?"),
            "names {craft} once",
        ),
        (
            lambda body: body["families"][0]["kinds"][0]["questions"].__setitem__(0, "Why is {craft} red?"),
            "singular or plural",
        ),
        (
            lambda body: body["families"][0]["kinds"][0]["questions"].__setitem__(
                0, "What gives {craft} its colours?"
            ),
            "singular or plural",
        ),
        (
            lambda body: body["families"][0]["kinds"][0]["otherQuestions"].__setitem__(0, "Why {craft}?"),
            "names no craft",
        ),
        (lambda body: body["families"][0]["kinds"][0].pop("otherQuestions"), "lists no questions"),
        (lambda body: body["families"][0].update(label=" Textiles"), "without outer spaces"),
        (lambda body: body["families"].append(body["families"][0]), "repeated"),
    ],
)
def test_a_malformed_file_is_refused(change: Any, message: str) -> None:
    body = raw()
    change(body)
    with pytest.raises(ValueError, match=message):
        parse_craft_families(body, load_master())
