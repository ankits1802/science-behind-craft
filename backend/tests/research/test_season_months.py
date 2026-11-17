import copy

import pytest
from pydantic import TypeAdapter

from app.research.calendar import only_season, season_months, year_months
from app.research.explainer import Block

from ..contracts.phase_b_golden import phase_b_blocks

BAGRU_QUOTE = (
    "Bagru has a semi-arid hot climate with monsoon months bringing in 650mm of rain from June to "
    "September, the summer months of April to early July having average daily temperatures of around "
    "30Â°C and the winter months of November to February are chilly with average"
)
JUNE_TO_SEPTEMBER = frozenset({6, 7, 8, 9})


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Printing runs from October to March.", {10, 11, 12, 1, 2, 3}),
        ("Geographical Indications Journal 188 dated December 19, 2023", set()),
        ("Azera Parveen Rahman 16 Oct 2019", set()),
        ("Shilp Guru and National Award Date :29-Nov-2022", set()),
        ("Issue-11* December- 2019", set()),
        ("listed for April 2009 to March 2010", set()),
        ("on June 5th 2003 there are 8 clusters", set()),
        ("Dyeing resumes in October, after the rains.", {10}),
        ("Rain falls from June–September.", {6, 7, 8, 9}),
    ],
)
def test_months_of_the_year_leave_out_dates(text: str, expected: set[int]) -> None:
    assert year_months([text]) == expected


def test_a_source_that_states_a_season_s_months_maps_it() -> None:
    assert season_months(BAGRU_QUOTE) == {"MONSOON": JUNE_TO_SEPTEMBER, "WINTER": frozenset({11, 12, 1, 2})}


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("The June to September monsoon fills the tanks.", {"MONSOON": JUNE_TO_SEPTEMBER}),
        ("Work stops in the monsoon (July to September).", {"MONSOON": frozenset({7, 8, 9})}),
        ("The cold season, from November to February, suits indigo.", {"WINTER": frozenset({11, 12, 1, 2})}),
        ("From June to September, the monsoon brings rain.", {"MONSOON": JUNE_TO_SEPTEMBER}),
        ("Summer comes first. From June to September the rains fall.", {"MONSOON": JUNE_TO_SEPTEMBER}),
        ("The monsoon arrives in June.", {}),
        ("The monsoon starts on 15 June and lasts to September.", {}),
        ("Monsoon rain falls from June to September; elsewhere the monsoon is July to August.", {}),
        ("Winter is busy and work from June to September stops.", {}),
        ("Dyeing resumes after the monsoon, from October to March.", {}),
        ("The monsoon stops printing, which resumes from October to March.", {}),
        ("The summer, unlike the June to September monsoon, is dry.", {"MONSOON": JUNE_TO_SEPTEMBER}),
        ("Pre-monsoon showers come from April to May.", {}),
    ],
)
def test_a_season_is_mapped_only_where_its_words_meet_a_month_range(
    text: str, expected: dict[str, frozenset[int]]
) -> None:
    assert season_months(text) == expected


@pytest.mark.parametrize(
    "text",
    [
        "Block printing is not done during the monsoon.",
        "Cloth is never dried when it rains.",
        "Dyeing is done in every month except the monsoon.",
        "Printing stops from June to September.",
        "Jan Smith recorded the dyers in 1990.",
    ],
)
def test_a_month_or_season_its_clause_rules_out_times_nothing(text: str) -> None:
    assert (year_months([text]), only_season(text)) == (frozenset(), None)


@pytest.mark.parametrize(
    ("text", "months", "season"),
    [
        ("Printing runs from October till March.", {10, 11, 12, 1, 2, 3}, None),
        ("Indigo vats are set in Jan. Work slows in the monsoon.", {1}, "MONSOON"),
        ("Dyeing isn't done in June, but printing runs in March.", {3}, None),
        ("Washing waits for the rains, and the cloth dries in winter.", set(), None),
    ],
)
def test_a_timing_its_clause_does_not_rule_out_is_kept(
    text: str, months: set[int], season: str | None
) -> None:
    assert (year_months([text]), only_season(text)) == (months, season)


def test_a_row_reads_one_season_or_none() -> None:
    assert only_season("Monsoon humidity slows production.") == "MONSOON"
    assert only_season("Printing in winter, never in the monsoon.") is None
    assert only_season("Blocks are carved from teak.") is None
    assert only_season("Post-monsoon dyeing is brisk.") is None


def test_a_stage_may_be_listed_without_a_month_but_another_row_may_not() -> None:
    body = copy.deepcopy(phase_b_blocks()["s3.b1"])
    body["rows"][0].update(stageId="7f1a8e8e-5b0c-5d36-9c1a-55b1bb6f2b80", months=[], season=None)
    block = TypeAdapter(Block).validate_python(body)
    assert (block.rows[0].months, block.rows[0].season) == ([], None)
