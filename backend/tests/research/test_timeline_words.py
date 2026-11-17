import pytest

from app.research.timeline import states_movement, years_named


@pytest.mark.parametrize(
    ("text", "spans"),
    [
        ("Rao Bharmalji I (1586-1631) invited printers", {(1586, 1631), (1586, 1586), (1631, 1631)}),
        ("1855 - ca. 1879 (made)", {(1855, 1879), (1855, 1855), (1879, 1879)}),
        ("made ca. 1855-79 in Sind", {(1855, 1879), (1855, 1855)}),
        ("from 1947 to 2001", {(1947, 2001), (1947, 1947), (2001, 2001)}),
        ("In 2001, an earthquake struck", {(2001, 2001)}),
        ("15th-century fragments", {(1401, 1500)}),
        ("dated back to the fifteenth century", {(1401, 1500)}),
        ("cotton fragments from the 11th-14th century AD", {(1001, 1400)}),
        ("During the 7th century, the Khatris", {(601, 700)}),
        ("by the early 1950s synthetic dyes", {(1950, 1959)}),
        ("in the twenty-first century", {(2001, 2100)}),
        ("the 3rd century BCE", set()),
        ("about 1500 BC", set()),
        ("3000 year old strands", set()),
        ("over 100 families and 30 workshops", set()),
        ("RS 1.5 crore and 2,500 a month", set()),
        ("some 400 years ago", set()),
    ],
)
def test_years_are_only_those_a_text_states(text: str, spans: set[tuple[int, int]]) -> None:
    assert years_named([text]) == spans


def test_years_are_read_from_every_text_and_typographic_dashes() -> None:
    assert years_named(["In 2001", "the years 1586–1631"]) == {
        (2001, 2001),
        (1586, 1631),
        (1586, 1586),
        (1631, 1631),
    }


QUOTE = (
    "The erstwhile ruler of Kutch Rao Bharmalji - I (1586-1631), invited the cloth-printing Khatri "
    "artisans from Sindh and gave them permission to settle and earn their livelihoods anywhere in Kutch."
)


@pytest.mark.parametrize(
    ("texts", "start", "end", "moves"),
    [
        ([QUOTE], "Sindh", "Kutch", True),
        ([QUOTE], "Kutch", "Sindh", False),
        (["to migrate from Sind and settle in Dhamadka, Kachchh."], "Sind", "Dhamadka", True),
        (["Indigo came from Shikarpur in Sindh."], "Shikarpur", "Sindh", True),
        (["Printers in Sindh and Kutch used madder."], "Sindh", "Kutch", False),
        (["Cloth from Sindh was admired in Kutch."], "Sindh", "Kutch", False),
        (["They came from Sindh.", "They settled in Kutch."], "Sindh", "Kutch", False),
        (["the village moved from Dhamadkas to Ajrakhpur"], "Dhamadka", "Ajrakhpur", False),
    ],
)
def test_a_route_is_a_move_one_text_states_from_its_start_to_its_end(
    texts: list[str], start: str, end: str, moves: bool
) -> None:
    assert states_movement(texts, start, end) is moves
