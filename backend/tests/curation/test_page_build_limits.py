import uuid
from types import SimpleNamespace
from typing import Any

from app.composer.timeline_map import TimelinePointChoice, TimelineRouteChoice
from app.research.crafts import CraftRef
from app.science.records import KnownClaim, ProcessRecords
from app.services.chapter_context import ChapterContext
from app.services.chapter_history import timeline_choice

OUTSIDE = uuid.UUID(int=41)
CRAFT = CraftRef(slug="Test-Craft", name="Test Craft", path="/crafts/Test-Craft")


def test_a_history_timeline_over_many_dated_places_stays_within_the_choice_s_limits() -> None:
    points = [TimelinePointChoice(statement=f"c{n}", place=f"Place {n}", years="y1") for n in range(1, 28)]
    routes = [TimelineRouteChoice(statement=f"c{n}", start="A", end="B", years="y1") for n in range(1, 15)]
    choice = timeline_choice(points, routes)
    assert (len(choice.points), len(choice.routes)) == (24, 12)
    assert (choice.points, choice.routes) == (points[:24], routes[:12])


def test_the_page_ladder_reads_only_claims_the_page_lists_and_keeps_its_process_sources() -> None:
    stored = ProcessRecords(
        craft=CRAFT,
        processes=(),
        stages=(),
        materials=(),
        reactions=(),
        conditions=(),
        claims={OUTSIDE: KnownClaim(OUTSIDE, "A shared stage concept's claim.", "PROVISIONAL", ())},
        sources={"S9": "the process's own source"},
    )
    records: Any = SimpleNamespace(process=stored, sources={"S1": "the page's source"}, curated=None)
    rows: Any = SimpleNamespace(record_sources={})
    context = ChapterContext(records, rows, {}, None)  # type: ignore[arg-type]
    process = context.process()
    assert OUTSIDE not in process.claims
    assert set(process.sources) == {"S1", "S9"}
