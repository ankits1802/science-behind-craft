import uuid
from typing import Any

import pytest

from app.core.errors import ExternalFailure
from app.services import upkeep_quotes
from app.services.upkeep_quotes import (
    QUOTE_SOURCES_PER_NIGHT,
    CitedQuote,
    DueSource,
    check_source,
    quote_verdicts,
    recheck_quotes,
)

from .fakes import NIGHT, ScriptedFetcher, fetched_page, gone

KEPT = uuid.UUID(int=1)
LOST = uuid.UUID(int=2)
EN_DASH = chr(0x2013)
CURLY_APOSTROPHE = chr(0x2019)
PAGE = f"Alum, a double sulphate, binds the madder red to the cotton.\nIt is boiled for an hour {EN_DASH} the dyer's rule."
PAGE_URL = "https://crafts.example.org/ajrakh/mordants"
GONE_URL = "https://crafts.example.org/ajrakh/missing"
ROBOTS_URL = "https://crafts.example.org/ajrakh/private"


def test_a_quote_found_in_the_fetched_text_passes_and_one_missing_fails() -> None:
    quotes = [
        CitedQuote(KEPT, "binds the Madder red to the cotton"),
        CitedQuote(LOST, "fixes the indigo blue"),
    ]
    assert quote_verdicts(PAGE, truncated=False, quotes=quotes) == {KEPT: "PASS", LOST: "FAIL"}


def test_line_breaks_dashes_and_curly_apostrophes_do_not_fail_a_quote() -> None:
    quotes = [
        CitedQuote(KEPT, "cotton. It is boiled for an hour"),
        CitedQuote(LOST, f"an hour - the dyer{CURLY_APOSTROPHE}s rule"),
    ]
    assert quote_verdicts(PAGE, truncated=False, quotes=quotes) == {KEPT: "PASS", LOST: "PASS"}


def test_a_missing_quote_in_a_truncated_text_stays_undecided() -> None:
    quotes = [CitedQuote(KEPT, "binds the madder red"), CitedQuote(LOST, "fixes the indigo blue")]
    assert quote_verdicts(PAGE, truncated=True, quotes=quotes) == {KEPT: "PASS"}


class Recorded:
    def __init__(self) -> None:
        self.fetches: list[tuple[uuid.UUID, str, str | None]] = []
        self.verdicts: dict[uuid.UUID, str] = {}
        self.limits: list[int] = []
        self.commits = 0

    async def commit(self) -> None:
        self.commits += 1


@pytest.fixture
def recorded(monkeypatch: pytest.MonkeyPatch) -> Recorded:
    seen = Recorded()
    due = [
        DueSource(
            uuid.UUID(int=10),
            PAGE_URL,
            (CitedQuote(KEPT, "binds the madder red"), CitedQuote(LOST, "indigo")),
        ),
        DueSource(uuid.UUID(int=11), GONE_URL, (CitedQuote(uuid.UUID(int=3), "anything at all here"),)),
        DueSource(uuid.UUID(int=12), ROBOTS_URL, ()),
    ]

    async def sources_due(session: Any, *, now: Any, limit: int) -> list[DueSource]:
        seen.limits.append(limit)
        return due[:limit]

    async def record_fetch(
        session: Any, source_id: uuid.UUID, *, outcome: str, problem: str | None, now: Any
    ) -> None:
        seen.fetches.append((source_id, outcome, problem))

    async def record_verdicts(session: Any, verdicts: dict[uuid.UUID, str], now: Any) -> None:
        seen.verdicts.update(verdicts)

    monkeypatch.setattr(upkeep_quotes, "sources_due", sources_due)
    monkeypatch.setattr(upkeep_quotes, "record_fetch", record_fetch)
    monkeypatch.setattr(upkeep_quotes, "_record_verdicts", record_verdicts)
    return seen


async def test_each_source_records_its_fetch_outcome_and_its_quotes(recorded: Recorded) -> None:
    fetcher = ScriptedFetcher({PAGE_URL: fetched_page(PAGE_URL, PAGE), GONE_URL: gone(GONE_URL)})
    report = await recheck_quotes(recorded, fetcher, now=NIGHT)  # type: ignore[arg-type]
    assert recorded.limits == [QUOTE_SOURCES_PER_NIGHT] == [50]
    assert recorded.fetches == [
        (uuid.UUID(int=10), "FETCHED", None),
        (uuid.UUID(int=11), "FAILED", "not_found 404"),
        (uuid.UUID(int=12), "REFUSED", "ROBOTS_DISALLOWED"),
    ]
    assert recorded.verdicts == {KEPT: "PASS", LOST: "FAIL"}
    assert report.as_dict() == {
        "sourcesChecked": 3,
        "fetched": 1,
        "refused": 1,
        "unreachable": 1,
        "quotesPassed": 1,
        "quotesFailed": 1,
        "quotesUndecided": 0,
        "fetcherUnavailable": False,
    }
    assert recorded.commits == 1


async def test_the_night_checks_no_more_sources_than_its_bound(recorded: Recorded) -> None:
    fetcher = ScriptedFetcher({PAGE_URL: fetched_page(PAGE_URL, PAGE)})
    report = await recheck_quotes(recorded, fetcher, now=NIGHT, limit=2)  # type: ignore[arg-type]
    assert fetcher.asked == [PAGE_URL, GONE_URL]
    assert len(report.checks) == 2


def fetcher_away() -> ExternalFailure:
    return ExternalFailure("the fetcher could not be reached", kind="unavailable", service="fetcher")


async def test_a_night_when_the_fetcher_is_away_blames_no_source(recorded: Recorded) -> None:
    away = fetcher_away()
    report = await recheck_quotes(
        recorded,  # type: ignore[arg-type]
        ScriptedFetcher({PAGE_URL: away, GONE_URL: away, ROBOTS_URL: away}),
        now=NIGHT,
    )
    assert report.fetcher_unavailable is True
    assert (recorded.fetches, recorded.verdicts, recorded.commits) == ([], {}, 0)


async def test_two_unreachable_sources_are_not_yet_an_outage(recorded: Recorded) -> None:
    away = fetcher_away()
    fetcher = ScriptedFetcher({PAGE_URL: away, GONE_URL: away})
    report = await recheck_quotes(recorded, fetcher, now=NIGHT, limit=2)  # type: ignore[arg-type]
    assert report.fetcher_unavailable is False
    assert [outcome for _, outcome, _ in recorded.fetches] == ["FAILED", "FAILED"]


async def test_an_address_that_is_not_a_fetchable_url_is_refused_without_a_fetch() -> None:
    fetcher = ScriptedFetcher({})
    check = await check_source(fetcher, DueSource(uuid.UUID(int=13), "https://", ()))
    assert fetcher.asked == []
    assert (check.outcome, check.problem) == ("REFUSED", "BAD_URL")
