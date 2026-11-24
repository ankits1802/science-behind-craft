import uuid
from dataclasses import replace
from typing import Any

import pytest

from app.research.craft_page import CraftPage
from app.research.monograph_document import MonographDocument
from app.research.monograph_page import CitedSource
from app.services.document_components import document_structure
from app.services.knowledge_view import ClaimView
from app.services.monograph_generated_assembly import GeneratedParts, assembled_document
from app.services.monograph_generated_drawings import Drawings
from app.services.monograph_generated_structure import with_page_claims
from app.services.monograph_generated_units import SubjectRecord, stored_source

from ..contracts.golden import golden_json
from .colour_key_parts import (
    BLUE_FACT,
    BLUE_QUOTE,
    BLUE_STAGE,
    KEY,
    SHIFTS,
    WHY_FACT,
    WHY_TEXT,
    YELLOW_FACT,
    YELLOW_QUOTE,
    YELLOW_STAGE,
    keyed,
    mordants_and_a_dye,
    stage,
    structure,
    text_of,
    with_why,
)
from .generated_parts import TEXT_ALUM


def test_two_colours_draw_a_key_opening_the_chemistry_one_as_its_swatch_pair_one_in_words() -> None:
    document = keyed(structure(with_why(BLUE_STAGE, WHY_TEXT), YELLOW_STAGE))
    (component,) = [c for c in document.content.components if c.kind == "swatch_cards"]
    assert (component.label, component.chapter, component.field) == (KEY, "chem", "CHEMISTRY")
    assert component.title == "Two colours and what gives each"
    spec = document.specs[KEY]
    assert (spec["titleId"], spec["weave"]) == ("colour-key-h", "mb-weave")
    assert [text_of(document, spec[key]) for key in ("chapterNo", "title", "intro")] == [
        "Colour key",
        "Two colours and what gives each",
        "Blue and yellow.",
    ]
    blue, yellow = spec["colours"]
    assert blue == {
        "before": {"dye": "leuco", "caption": "u8904"},
        "join": "becomes",
        "after": {"dye": "indigo", "caption": "u8905"},
        "name": "u8906",
        "agent": "u8907",
        "text": "u8908",
        "why": "u8909",
    }
    assert yellow == {"name": "u8910", "agent": "u8911", "text": "u8912"}
    assert [text_of(document, f"u{n}") for n in range(8904, 8913)] == [
        "Green",
        "Indigo dyeing",
        "Blue",
        "Indigo",
        "Blue in the air.",
        WHY_TEXT,
        "Yellow",
        "Marigold",
        "A bright yellow.",
    ]
    chem = [(e.ref, e.within) for e in document.content.layout if e.chapter == "chem"]
    assert chem[:2] == [("chapter-chem", None), (KEY, None)]
    assert [ref for ref, within in chem if within == KEY] == [f"u{n}" for n in range(8901, 8913)]


def test_each_swatch_s_sentence_cites_the_fact_that_names_its_colour() -> None:
    document = keyed(structure(with_why(BLUE_STAGE, WHY_TEXT), YELLOW_STAGE))
    content = document.content
    for unit, claim, quote in (
        ("u8908", BLUE_FACT, BLUE_QUOTE),
        ("u8909", WHY_FACT, "indigo oxidises to its blue form"),
        ("u8912", YELLOW_FACT, YELLOW_QUOTE),
    ):
        (cited,) = content.citations[unit]
        assert (cited.quote, cited.locator, content.sources[cited.source].title) == (
            quote,
            "p. 4",
            "Dyeing notes",
        )
        assert content.citation_claims[unit] == [str(claim)]
        assert content.units[unit].claim_ids == [str(claim)]
    assert all(not content.units[f"u{n}"].claim_ids for n in (8901, 8902, 8903, 8904, 8905, 8906, 8907))


def test_a_why_the_page_already_tells_is_left_off_its_card() -> None:
    document = keyed(structure(with_why(BLUE_STAGE, TEXT_ALUM), YELLOW_STAGE))
    blue, _ = document.specs[KEY]["colours"]
    assert "why" not in blue and blue["text"] == "u8908"


@pytest.mark.parametrize(
    ("stages", "hidden"),
    [
        ((BLUE_STAGE,), ()),
        ((stage(1, "Indigo dyeing", "Indigo", None), stage(2, "Turmeric dyeing", "Turmeric", None)), ()),
        ((BLUE_STAGE, YELLOW_STAGE), (YELLOW_FACT,)),
    ],
)
def test_a_page_whose_shown_facts_name_fewer_than_two_colours_draws_no_key(
    stages: tuple[dict[str, Any], ...], hidden: tuple[uuid.UUID, ...]
) -> None:
    document = keyed(structure(*stages), *hidden)
    assert KEY not in document.specs
    assert all(c.kind != "swatch_cards" for c in document.content.components)
    assert all(not unit.startswith("u89") for unit in document.content.units)


def golden_document() -> MonographDocument:
    page = CraftPage.model_validate(golden_json("craft.page.golden.json"))
    shown = document_structure(page)
    visible = {
        claim.id: ClaimView(
            claim.id,
            claim.text,
            claim.level,
            "MATERIAL",
            None,
            citations=[
                {"sourceId": c.source_id, "quote": c.quote, "locator": c.locator} for c in claim.citations
            ],
        )
        for claim in page.claims
    }
    sources: dict[str, CitedSource] = {s.id: stored_source(s.model_dump(mode="json")) for s in page.sources}
    parts = GeneratedParts(
        subject_kind="craft",
        subject_slug="Kutch-Ajrakh",
        page_url="https://kalavigyan.example/crafts/Kutch-Ajrakh",
        record=SubjectRecord(name=page.craft.name, kicker="Textiles", place="Kachchh, Gujarat", gi=True),
        sections=tuple(replace(section, version=1) for section in with_page_claims([], shown)),
        visible=visible,
        sources=sources,
        structure=shown,
    )
    built = assembled_document(parts, Drawings())
    assert built is not None
    return built


def test_kutch_ajrakh_s_stages_key_five_colours_each_by_the_dye_its_stage_names() -> None:
    document = golden_document()
    spec = document.specs["kutch-ajrakh/chemistry/colour-key"]
    cards = spec["colours"]
    assert [text_of(document, card["name"]) for card in cards] == ["Yellow", "White", "Black", "Blue", "Red"]
    assert [card["after"]["dye"] for card in cards] == ["harda", "lime", "kut", "indigo", "madder"]
    assert [text_of(document, card["agent"]) for card in cards] == [
        "Myrobalan (harda)",
        "Lime",
        "Ferrous sulphate, Scrap iron",
        "Indigo",
        "Al root, Alizarin, Madder",
    ]
    assert [text_of(document, card["after"]["caption"]) for card in cards] == [
        "Myrobalan treatment",
        "Outline resist printing",
        "Iron-black printing",
        "Indigo dyeing",
        "Red dyeing",
    ]
    assert [text_of(document, card["text"]) for card in cards] == [
        "A yellow tinge from the harda.",
        "White outlines printed in resist.",
        "Black outlines.",
        "Rich blue, built up by immersions in the vat.",
        "Red where pa and gach were printed.",
    ]
    assert all("before" not in card for card in cards)
    assert text_of(document, spec["title"]) == "Five colours and what gives each"
    assert text_of(document, spec["intro"]) == "Yellow, white, black, blue and red."


def test_each_mordant_s_shift_and_a_dye_s_stated_colour_join_the_key_in_the_order_told() -> None:
    document = keyed(mordants_and_a_dye())
    spec = document.specs[KEY]
    red, black, yellow = spec["colours"]
    assert red == {
        "after": {"dye": "madder", "caption": "u8904"},
        "name": "u8905",
        "agent": "u8906",
        "text": "u8907",
    }
    assert black == {"name": "u8908", "agent": "u8909", "text": "u8910"}
    assert yellow == {"name": "u8911", "agent": "u8912", "text": "u8913"}
    assert [text_of(document, f"u{n}") for n in range(8904, 8914)] == [
        "alum",
        "Red",
        "Madder on alum",
        SHIFTS[0][1],
        "Black",
        "Madder on iron",
        SHIFTS[1][1],
        "Yellow",
        "Marigold flowers",
        SHIFTS[2][1],
    ]
    assert text_of(document, spec["title"]) == "Three colours and what gives each"
    assert text_of(document, spec["intro"]) == "Red, black and yellow."
