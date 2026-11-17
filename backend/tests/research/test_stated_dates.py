import pytest
from pydantic import ValidationError

from app.research.blocks import ExplainerSentence
from app.research.blocks_insight import GiStatus, PriceRange
from app.research.citations import Citation
from app.research.stated_dates import first_day_date, stated_dates, stated_precision, states_date

CLAIM = "8f0c1f7e-3a1b-4c2d-9e8f-0a1b2c3d4e5f"


@pytest.mark.parametrize(
    ("text", "dates"),
    [
        ("Certificate Date 11-05-2011", ["2011-05-11"]),
        ("registered on 22/04/2024", ["2024-04-22"]),
        ("filed on 31st January, 2023", ["2023-01-31"]),
        ("filed on January 31, 2023", ["2023-01-31"]),
        ("dated 2024-04-22 in the journal", ["2024-04-22"]),
        ("published in Sept. 2019", ["2019-09"]),
        ("on 2 April 2024, and again in May 2025", ["2024-04-02", "2025-05"]),
        ("prices may 2024 rise", []),
        ("valued at Rs. 7 in 1975", []),
        ("31-02-2020 is no day", []),
    ],
)
def test_the_dates_a_text_states_are_read_at_their_own_precision(text: str, dates: list[str]) -> None:
    assert stated_dates(text) == dates


def test_the_first_full_date_after_a_label_is_the_earliest_in_the_window() -> None:
    assert first_day_date("Journal 37 of 4 May 2010, certificate 11-05-2011") == "2010-05-04"
    assert first_day_date("in April 2024") is None


@pytest.mark.parametrize(
    ("value", "texts", "stated"),
    [
        ("2024-04-22", ["Registered 22-04-2024"], True),
        ("2024-04-02", ["Registered 22-04-2024"], False),
        ("2024-04", ["Registered 22-04-2024"], True),
        ("2024-04", ["Registered in 2024"], False),
        ("2024", ["Registered 22-04-2024"], True),
        ("2023", ["Registered 22-04-2024"], False),
    ],
)
def test_a_date_is_stated_only_at_the_precision_a_text_gives(
    value: str, texts: list[str], stated: bool
) -> None:
    assert states_date(value, texts) is stated


@pytest.mark.parametrize(
    ("value", "kept"),
    [
        ("2024-04-22", "2024-04-22"),
        ("2024-04-02", "2024-04"),
        ("2024-03-22", "2024"),
        ("2019-04-22", None),
    ],
)
def test_a_curated_date_is_cut_to_what_its_texts_state(value: str, kept: str | None) -> None:
    assert stated_precision(value, ["Registered on 22-04-2024 in GI Journal 188"]) == kept


def sentence(text: str, quote: str) -> ExplainerSentence:
    citation = Citation(
        id="c1",
        claim_id=CLAIM,
        source_id="s-gi",
        quote=quote,
        locator="p. 1",
        context=None,
        evidence="QUOTED",
        level="PROVISIONAL",
    )
    return ExplainerSentence(id="s5.b1.1", text=text, level="PROVISIONAL", citations=[citation], terms=[])


def gi_status(registered_on: str) -> GiStatus:
    return GiStatus(
        status="REGISTERED",
        application_number="1050",
        certificate_number=None,
        filed_on=None,
        registered_on=registered_on,
        journal_issue=None,
        proprietors=[],
        authorised_user_count=None,
        sentences=[sentence("Kutch Ajrakh is a registered GI, application 1050.", "Registered 22-04-2024")],
    )


def test_a_gi_record_shows_a_day_only_when_its_sentences_state_that_day() -> None:
    assert gi_status("2024-04-22").registered_on == "2024-04-22"
    assert gi_status("2024-04").registered_on == "2024-04"
    with pytest.raises(ValidationError, match="2024-04-02"):
        gi_status("2024-04-02")


def price(priced_on: str) -> PriceRange:
    return PriceRange(
        stated="Rs. 7",
        low=7,
        high=None,
        currency="INR",
        scale=None,
        per=None,
        priced_on=priced_on,
        place="Barmer",
        district_lgd=90,
        sentence=sentence("In Barmer an ajrakh piece was valued at Rs. 7 in 1975.", "Rs. 7 in 1975, Barmer"),
    )


def test_a_price_is_dated_no_more_precisely_than_its_sentence() -> None:
    assert price("1975").priced_on == "1975"
    with pytest.raises(ValidationError, match="precisely"):
        price("1975-03")
