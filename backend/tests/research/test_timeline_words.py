import pytest

from app.research.timeline import ordinal, states_movement, year_span_text, years_named, years_offered


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
        ("Indian cotton fragments of the 11th to 14th century", {(1001, 1400)}),
        ("main source of revenue during the 18th and 19th centuries", {(1701, 1900)}),
        ("a port of the Pallava dynasty from the sixth to ninth century CE", {(501, 900)}),
        ("surviving pieces date from the late 16th or early 17th century", {(1501, 1700)}),
        ("flourished from the early 18th to the mid-20th century", {(1701, 2000)}),
        ("held sway till about the mid-18th century", {(1701, 1800)}),
        ("rotary querns reached India in the 3rd and 4th centuries CE", {(201, 400)}),
        ("the 3rd and 2nd centuries BCE", set()),
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


@pytest.mark.parametrize(
    ("text", "spans"),
    [
        ("In 1930 hundreds of Indian cotton fragments were found at Al Fustat", {(1930, 1930)}),
        ("pots heated to 1250-1280°C, and melting takes about 16-18 hours", set()),
        ("raises the fire to about 1000-1200 degrees Celsius", set()),
        ("a glob of molten glass at around 1300 °C", set()),
        ("About 1450 million years ago the Delhi Orogeny metamorphosed the limestones", set()),
        ("a 2019 study put the cluster's annual business at more than Rs 2000 crore", {(2019, 2019)}),
        ("In 1975 a metre cost Rs. 1500 at Barmer", {(1975, 1975)}),
    ],
)
def test_measures_and_sums_are_not_offered_as_years(text: str, spans: set[tuple[int, int]]) -> None:
    assert years_offered([text]) == spans


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


@pytest.mark.parametrize(
    ("start", "end", "words"),
    [
        (1586, 1586, "1586"),
        (1586, 1631, "1586–1631"),
        (1401, 1500, "15th century"),
        (1001, 1400, "11th–14th century"),
        (2001, 2100, "21st century"),
        (1950, 1959, "1950s"),
        (1400, 1500, "1400–1500"),
        (1401, 1499, "1401–1499"),
        (1950, 1960, "1950–1960"),
        (1951, 1960, "1951–1960"),
        (-500, -500, "500 BCE"),
        (-499, -400, "499 BCE–400 BCE"),
    ],
)
def test_a_span_of_years_is_written_as_the_web_writes_a_timeline_s_span(
    start: int, end: int, words: str
) -> None:
    assert year_span_text(start, end) == words


def test_an_ordinal_takes_th_for_the_teens_and_st_nd_rd_after_them() -> None:
    assert [ordinal(n) for n in (1, 2, 3, 4, 11, 12, 13, 21, 22, 23, 111, 112, 113, 121)] == [
        "1st",
        "2nd",
        "3rd",
        "4th",
        "11th",
        "12th",
        "13th",
        "21st",
        "22nd",
        "23rd",
        "111th",
        "112th",
        "113th",
        "121st",
    ]
