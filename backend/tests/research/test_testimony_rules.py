import pytest

from app.research.testimony import (
    CONTRIBUTION_MOVES,
    NAME_HELD_BACK,
    Draft,
    contribution_problems,
    credit_name_problem,
    held_back_terms,
    move_allowed,
    quote_span,
    screens_for,
    speaker,
    time_locator,
)

TURN = "Yes. We keep the indigo vat warm for 3 days, and we stir it every morning before work."
GOOD = Draft(
    quote="We keep the indigo vat warm for 3 days",
    english="We keep the indigo vat warm for 3 days",
    claim="The indigo vat is kept warm for 3 days.",
    discipline="PROCESS",
    concept_type="PROCESS_STAGE",
    concept_name="Indigo vat",
)


@pytest.mark.parametrize(
    ("mode", "name", "short", "line", "shown"),
    [
        (
            "FULL_NAME",
            "Ismail Mohammed Khatri",
            "Ismail",
            "Ismail Mohammed Khatri, Ajrakh, Kachchh, Gujarat",
            "Ismail Mohammed Khatri",
        ),
        ("FIRST_NAME", "Ismail Mohammed Khatri", "Ismail", "Ismail, Ajrakh, Kachchh, Gujarat", "Ismail"),
        (
            "CRAFT_AND_DISTRICT",
            "Ismail Mohammed Khatri",
            "Ismail",
            "An artisan of Ajrakh, Kachchh, Gujarat",
            None,
        ),
    ],
)
def test_the_speaker_line_follows_the_credit_mode(
    mode: str, name: str, short: str, line: str, shown: str | None
) -> None:
    found = speaker(
        mode=mode, name=name, short_name=short, craft="Ajrakh", district="Kachchh", state="Gujarat"
    )
    assert (found.line, found.name, found.role, found.district, found.state) == (
        line,
        shown,
        "ARTISAN",
        "Kachchh",
        "Gujarat",
    )


def test_locators_read_minutes_and_seconds_and_hours_past_an_hour() -> None:
    assert time_locator(65_000, 83_500, "WORD") == "1:05–1:23"
    assert time_locator(3_725_000, 3_731_000, "WORD") == "1:02:05–1:02:11"
    assert time_locator(5_000, 9_000, "TURN") == "at 0:05"


@pytest.mark.parametrize("name", ["Ismail", "Ismail M. Khatri", "D'Souza-Rao", "इस्माइल खत्री", "ਗੁਰਪ੍ਰੀਤ"])
def test_a_name_in_any_script_is_accepted(name: str) -> None:
    assert credit_name_problem(name, limit=120) is None


@pytest.mark.parametrize("name", ["", "  ", "Ismail 2", "ismail@example.com", "Call 9876543210", "x" * 61])
def test_a_name_with_digits_contacts_or_too_long_is_refused(name: str) -> None:
    assert credit_name_problem(name, limit=60) is not None


def test_held_back_terms_follow_the_credit_choice() -> None:
    full = held_back_terms(
        account_name="Ismail Mohammed Khatri", mode="FULL_NAME", credit_name=None, short_name=None
    )
    first = held_back_terms(
        account_name="Ismail Mohammed Khatri", mode="FIRST_NAME", credit_name=None, short_name="Ismail"
    )
    craft = held_back_terms(
        account_name="Ismail Khatri",
        mode="CRAFT_AND_DISTRICT",
        credit_name="Ismail Bhai Khatri",
        short_name=None,
    )
    assert full == frozenset()
    assert first == {"mohammed", "khatri"}
    assert craft == {"ismail", "bhai", "khatri"}


def test_a_held_back_name_is_screened_only_as_a_whole_word() -> None:
    terms = frozenset({"khatri"})
    assert screens_for(["My father Khatri taught me"], terms) == [NAME_HELD_BACK]
    assert screens_for(["KHATRI showed me"], terms) == [NAME_HELD_BACK]
    assert screens_for(["The Khatriya way of dyeing"], terms) == []
    assert screens_for(["Khatri2 is a label"], terms) == []
    assert screens_for([None, "indigo"], terms) == []


def test_a_quote_span_starts_and_ends_on_whole_words() -> None:
    assert quote_span("the indigo vat", "We keep the indigo vat warm.") == (8, 22)
    assert quote_span("he indigo vat", "We keep the indigo vat warm.") is None
    assert quote_span("indigo va", "We keep the indigo vat warm.") is None
    text = "warm the vat, then warm the vat again"
    assert quote_span("warm the vat", text, near=17) == (19, 31)


def test_a_quote_may_end_with_its_sentence_punctuation() -> None:
    turn = "We cover the vat with sacks every night. Then we sleep."
    assert quote_span("We cover the vat with sacks every night.", turn) == (0, 40)
    assert quote_span("We cover the vat with sacks every night", turn) == (0, 39)
    assert quote_span("We cover the vat with sacks every nigh", turn) is None
    assert quote_span(". Then we sleep.", turn) is None


def test_a_draft_quoted_word_for_word_passes() -> None:
    assert contribution_problems(GOOD, TURN) == []


@pytest.mark.parametrize(
    ("change", "problem"),
    [
        ({"quote": "We keep the indigo pot warm for 3 days"}, "exact words"),
        ({"quote": "indigo vat"}, "20 to 300"),
        ({"english": "We keep the indigo vat warm for three days"}, "exactly the figures"),
        ({"claim": "The indigo vat is kept warm for 4 days."}, "every figure of the claim"),
        ({"claim": "Call 98765 43210 for the vat."}, "phone"),
        ({"discipline": "MAGIC"}, "disciplines"),
        ({"concept_type": "OPEN_QUESTION"}, "testimony may have"),
        ({"concept_name": " "}, "concept name"),
        ({"claim": "x" * 301}, "1 to 300"),
    ],
)
def test_each_check_drops_a_draft_that_breaks_it(change: dict[str, str], problem: str) -> None:
    draft = Draft(**{**GOOD.__dict__, **change})
    assert any(problem in found for found in contribution_problems(draft, TURN))


def test_statuses_move_only_as_the_contract_allows() -> None:
    assert move_allowed("PENDING", "APPROVED")
    assert move_allowed("APPROVED", "APPROVED")
    assert move_allowed("APPROVED", "REJECTED")
    assert not move_allowed("REJECTED", "APPROVED")
    assert not move_allowed("WITHDRAWN", "PENDING")
    assert not move_allowed("REJECTED", "WITHDRAWN")
    assert len(CONTRIBUTION_MOVES) == 6
