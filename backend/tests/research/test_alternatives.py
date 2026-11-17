import pytest

from app.research.alternatives import alternatives_named
from app.research.quotes import quote_occurs, spans_in_key

NAMES = {
    "madder": ("Indian madder", "madder", "majeeta"),
    "al": ("Al root", "al"),
    "alizarin": ("Synthetic alizarin", "Alizarin"),
    "clay": ("Clay",),
    "millet": ("Millet flour",),
    "lime": ("Lime",),
    "indigo": ("Indigo",),
}


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Cloth is boiled in tamarix with madder, al or alizarin.", [{"madder", "al", "alizarin"}]),
        (
            "Traditionally the red dyeing is done with madder or al root, whichever is available.",
            [{"madder", "al"}],
        ),
        ("Synthetic alizarin replaced madder.", [{"alizarin", "madder"}]),
        ("Synthetic dyes have largely replaced madder in Kutch, and alizarin superseded it too.", []),
        ("Alizarin rapidly superseded madder.", [{"alizarin", "madder"}]),
        ("Alizarin, first synthesised in 1868, superseded madder.", []),
        ("Use majeeta instead of alizarin.", [{"madder", "alizarin"}]),
        ("Madder or alizarin gives red. Clay or lime resists.", [{"madder", "alizarin"}, {"clay", "lime"}]),
    ],
)
def test_names_joined_by_an_alternative_word_are_alternatives(text: str, expected: list[set[str]]) -> None:
    assert [set(found) for found in alternatives_named(text, NAMES)] == expected


@pytest.mark.parametrize(
    "text",
    [
        "Gach is clay, millet flour, gum and alum or lime.",
        "Madder, alizarin and indigo are dyes of the craft.",
        "Madder was used for centuries before it was finally replaced by alizarin.",
        "The alum mordant is natural and is applied before madder.",
        "Madder or madder roots are steeped.",
    ],
)
def test_lists_far_gaps_words_inside_words_and_one_name_relate_nothing(text: str) -> None:
    assert alternatives_named(text, NAMES) == []


def test_the_longest_name_at_a_place_is_the_one_read() -> None:
    names = {"alizarin": ("Alizarin",), "synthetic": ("Synthetic alizarin",), "madder": ("madder",)}
    assert alternatives_named("Synthetic alizarin or madder", names) == [frozenset({"synthetic", "madder"})]


def test_spans_are_every_whole_word_occurrence_of_a_name() -> None:
    key = "al root, alum, al and natural al"
    assert spans_in_key("al", key) == [(0, 2), (15, 17), (30, 32)]
    assert spans_in_key("", key) == []
    assert quote_occurs("al", key) and not quote_occurs("alu", key)
