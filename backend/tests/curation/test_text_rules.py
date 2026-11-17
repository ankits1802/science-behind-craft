from __future__ import annotations

import pytest

from app.curation.duplicates import near_duplicates
from app.curation.matching import match_key, quote_chars, quote_found
from app.curation.sentences import figure_gaps, relationship_sentence, single_sentence, unsourced_hedges
from app.research.evidence import personal_data_in
from app.research.quotes import normalise_quote_lines


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Ajrakh is printed in Kachchh on cotton cloth.", True),
        ("It is printed in Kachchh. It is dyed in indigo.", False),
        ("The craft was recorded in Sindh c. 1500 by travellers.", True),
        ("Dr. Ismail Khatri prints ajrakh with natural dyes in Ajrakhpur.", True),
        ("M. A. Khatri printed the cloth shown in the museum.", True),
        ("Ajrakh is printed in Kachchh on cotton cloth", False),
        ("The synthetic dye arrived in 1868. Printers then changed recipes.", False),
        ("The resist paste is made of lime, gum arabic, etc. and dried in the sun.", True),
    ],
)
def test_a_claim_is_one_sentence(text: str, expected: bool) -> None:
    assert single_sentence(text) is expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("The saaj stage uses this material (GI method of production).", True),
        ("The khariyanu stage uses this tool.", True),
        ("Sequential order in the GI method of production.", True),
        ("Sequential step in the generalised Dabu resist-dye cycle.", True),
        ("Khatri printers in Ajrakhpur use natural indigo and madder dyes.", True),
        ("The mordant printing stage PRECEDES the madder dyeing stage.", True),
        ("Washing the cloth -> printing the outline with a block.", True),
        ("Alizarin is used today instead of madder roots in most workshops.", False),
        ("Indigo produces a blue colour that deepens with each dip in the vat.", False),
        ("The river water at Dhamadka carried iron, which darkened the black prints.", False),
        ("The printers of Ajrakhpur moved there from Dhamadka after the earthquake of 2001.", False),
        ("Traditionally this stage takes three days in the dry season.", False),
    ],
)
def test_relationship_sentences_are_found(text: str, expected: bool) -> None:
    assert relationship_sentence(text) is expected


def test_every_figure_and_unit_of_a_claim_is_in_a_quote() -> None:
    claim = "The cloth is boiled for 3 hours at 90 °C with 2 kg of madder."
    assert figure_gaps(claim, ["boiled for 3 hours at 90 °C with 2 kg of madder root"]) == []
    assert figure_gaps(claim, ["boiled for three hours at 90 degrees with 2 kg of madder"]) == ["3", "°C"]
    assert figure_gaps("Alum, KAl(SO4)2, fixes the red.", ["alum fixes the red on cotton"]) == ["KAl(SO4)2"]
    assert figure_gaps("Printers number 1,200 in the district.", ["some 1200 printers live there"]) == []
    assert (
        figure_gaps("About 60 families print ajrakh in the village.", ["गाँव में लगभग ६० परिवार अजरख छापते हैं"])
        == []
    )
    assert figure_gaps("About 50 families print in the village.", ["about 150 families print there"]) == [
        "50"
    ]


def test_a_hedge_needs_the_source_to_hedge() -> None:
    claim = "The craft probably began in Sindh and may have moved east."
    assert unsourced_hedges(claim, ["the craft began in Sindh and moved east"]) == ["probably", "may"]
    assert unsourced_hedges(claim, ["it probably began in Sindh and may have moved east"]) == []
    assert (
        unsourced_hedges("Printing stops in May before the monsoon arrives.", ["printing stops in May"]) == []
    )


@pytest.mark.parametrize(
    ("quote", "text", "expected"),
    [
        ("THE CLOTH IS WASHED IN THE RIVER", "after printing the cloth is washed in the river", True),
        ("the ‘saaj’ stage — washing", "then the 'saaj' stage - washing follows", True),
        ("the dyestuff is boiled", "first the dye-\nstuff is boiled with water", True),
        ("the mordant is fixed", "the mordant is ﬁxed by steaming", True),
        ("the cloth is dried", "the  cloth\n  is\tdried on sand", True),
        ("Ajrakh­ printing", "ajrakh printing", True),
        ("50 families", "about 150 families", False),
        ("printed with blocks", "printed with block prints", False),
    ],
)
def test_quotes_are_matched_after_normalisation(quote: str, text: str, expected: bool) -> None:
    assert quote_found(quote, match_key(text)) is expected


def test_source_text_keeps_its_lines_for_reading() -> None:
    raw = "Ajrakh  is “printed”\n\n\n on both sides of the dye-\n stuff\r\nlast line "
    assert normalise_quote_lines(raw) == ['Ajrakh is "printed"', "on both sides of the dyestuff", "last line"]


def test_quote_length_counts_normalised_characters() -> None:
    assert quote_chars("  the   cloth  ") == len("the cloth")


def test_near_identical_claims_are_paired_unless_linked_as_a_conflict() -> None:
    texts = [
        ("C001", "About 80 families practise ajrakh in Ajrakhpur."),
        ("C002", "About 100 families practise ajrakh in Ajrakhpur."),
        ("C003", "In Ajrakhpur, about 80 families practise ajrakh!"),
        ("C004", "The black is printed with an iron and jaggery liquid."),
    ]
    found = {(pair.first, pair.second) for pair in near_duplicates(texts)}
    assert found == {("C001", "C002"), ("C001", "C003"), ("C002", "C003")}
    linked = {frozenset({"C001", "C002"}), frozenset({"C002", "C003"})}
    assert {(pair.first, pair.second) for pair in near_duplicates(texts, linked=linked)} == {("C001", "C003")}


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Call the printer on +91 98765 43210 to order.", ["phone-like number"]),
        ("Write to printer@example.org for prices.", ["email address"]),
        ("His card reads 1234 5678 9012.", ["Aadhaar-like number", "phone-like number"]),
        ("The cooperative was formed in 1998 with 40 members.", []),
    ],
)
def test_personal_data_patterns(text: str, expected: list[str]) -> None:
    assert personal_data_in(text) == expected
