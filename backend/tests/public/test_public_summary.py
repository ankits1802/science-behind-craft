import asyncio
import dataclasses
import json
import uuid
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.api.routes import public
from app.core.db import get_session
from app.main import create_app
from app.models import User
from app.research.craft_page import CraftPage
from app.research.public_summary import PublicSummary
from app.services.curation_keys import curated_id
from app.services.public_summary import (
    SPECIMEN_CLAIM_KEY,
    SPECIMEN_CRAFT_SLUG,
    SummaryCache,
    curated_reading,
    public_summary,
)

from ..contracts.golden import dumped, golden_json, golden_text, reproduces
from ..readers import sign_in_as
from .summary_fixture import AJRAKH, DHOKRA, SUMMARY_GOLDEN, TIKULI, summary_fixture_records

CRAFT_PAGE_GOLDEN = "craft.page.golden.json"
PATH = "/api/public/summary"


def built() -> PublicSummary:
    return public_summary(summary_fixture_records())


def test_the_summary_golden_is_reproduced_byte_for_byte_from_its_records() -> None:
    assert dumped(PublicSummary, built()) == golden_text(SUMMARY_GOLDEN)
    assert reproduces(PublicSummary, SUMMARY_GOLDEN)


def test_the_counts_are_the_catalogue_summary() -> None:
    assert built().counts == summary_fixture_records().counts


def test_points_keep_only_reader_crafts_and_label_the_curated_ones() -> None:
    points = {point.key: point for point in built().points}
    assert sorted(points) == ["district-449", "state-10", "state-22", "state-24"]
    assert (points["state-10"].total, [craft.slug for craft in points["state-10"].curated]) == (2, [TIKULI])
    assert (points["state-24"].total, [craft.slug for craft in points["state-24"].curated]) == (2, [AJRAKH])
    assert points["district-449"].total == 1


def test_featured_crafts_keep_their_order_and_a_missing_hero_stays_explicit() -> None:
    featured = built().featured
    assert [entry.craft.slug for entry in featured] == [AJRAKH, DHOKRA, TIKULI]
    assert [entry.hero is not None for entry in featured] == [True, True, False]
    assert featured[0].lede.id == "pa1.1"
    assert featured[1].local_name == "Ghadwa kala"


def test_a_featured_craft_without_a_reading_or_a_lede_is_left_out() -> None:
    records = summary_fixture_records()
    readings = dict(records.readings)
    readings.pop(DHOKRA)
    readings[TIKULI] = dataclasses.replace(readings[TIKULI], lede=())
    summary = public_summary(dataclasses.replace(records, readings=readings))
    assert [entry.craft.slug for entry in summary.featured] == [AJRAKH]


def test_the_specimen_is_the_overview_sentence_citing_the_chosen_claim_with_every_quote() -> None:
    specimen = built().specimen
    assert specimen is not None and specimen.craft.slug == SPECIMEN_CRAFT_SLUG
    assert specimen.sentence.id == "pa2.1"
    claim = str(curated_id(SPECIMEN_CRAFT_SLUG, SPECIMEN_CLAIM_KEY))
    assert claim in {citation.claim_id for citation in specimen.sentence.citations}
    assert all(citation.quote for citation in specimen.sentence.citations)
    assert len(specimen.sentence.citations) == 3


def test_sources_are_every_cited_source_once_in_the_order_first_cited() -> None:
    summary = built()
    cited = [c.source_id for entry in summary.featured for c in entry.lede.citations]
    cited += [c.source_id for c in summary.specimen.sentence.citations] if summary.specimen else []
    assert [source.id for source in summary.sources] == list(dict.fromkeys(cited))
    assert len(summary.sources) == 8


def test_without_the_specimen_sentence_there_is_no_specimen_and_its_sources_go() -> None:
    records = summary_fixture_records()
    ajrakh = records.readings[AJRAKH]
    readings = {**records.readings, AJRAKH: dataclasses.replace(ajrakh, sentences=ajrakh.lede)}
    summary = public_summary(dataclasses.replace(records, readings=readings))
    assert summary.specimen is None
    assert len(summary.sources) == 6


def test_the_summary_carries_no_reader_data() -> None:
    text = golden_text(SUMMARY_GOLDEN)
    for key in ("email", "userId", "askedBy", "createdById", "ipHash", "role"):
        assert f'"{key}"' not in text


def test_a_craft_page_reads_as_its_lede_hero_and_cited_sentences() -> None:
    page = CraftPage.model_validate(golden_json(CRAFT_PAGE_GOLDEN))
    reading = curated_reading(page)
    assert reading.craft.slug == page.craft.slug
    assert [sentence.text for sentence in reading.lede] == [sentence.text for sentence in page.overview.lede]
    heroes = [picture for picture in page.pictures if picture.role == "HERO"]
    assert (reading.hero.media if reading.hero else None) == (heroes[0].media if heroes else None)
    claims = {claim.id: claim for claim in page.claims}
    first = page.overview.lede[0]
    expected = {c.id for claim_id in first.claim_ids for c in claims[claim_id].citations}
    assert {citation.id for citation in reading.lede[0].citations} == expected
    specimen = str(curated_id(SPECIMEN_CRAFT_SLUG, SPECIMEN_CLAIM_KEY))
    assert any(c.claim_id == specimen for sentence in reading.sentences for c in sentence.citations)


async def test_the_cache_builds_once_a_day_and_once_for_concurrent_readers() -> None:
    moments = iter([0.0, 10.0, 86_399.0, 86_401.0])
    cache = SummaryCache(clock=lambda: next(moments))
    builds: list[int] = []

    async def build() -> PublicSummary:
        builds.append(len(builds))
        await asyncio.sleep(0)
        return built()

    await asyncio.gather(cache.summary(build), cache.summary(build))
    await cache.summary(build)
    await cache.summary(build)
    assert builds == [0, 1]


async def no_session() -> Any:
    yield None


@pytest.fixture
def anonymous(monkeypatch: pytest.MonkeyPatch) -> tuple[TestClient, list[int]]:
    loads: list[int] = []

    async def records(_session: Any) -> Any:
        loads.append(1)
        return summary_fixture_records()

    monkeypatch.setattr(public, "summary_records", records)
    app = create_app()
    app.dependency_overrides[get_session] = no_session
    return TestClient(app), loads


def test_the_summary_route_answers_without_a_session_and_is_cached_a_day(
    anonymous: tuple[TestClient, list[int]],
) -> None:
    client, loads = anonymous
    response = client.get(PATH)
    assert response.status_code == 200
    assert response.json() == json.loads(golden_text(SUMMARY_GOLDEN))
    assert response.headers["cache-control"] == "public, max-age=86400"
    again = client.get(PATH, headers={"If-None-Match": response.headers["etag"]})
    assert (again.status_code, again.content) == (304, b"")
    assert loads == [1]


def test_a_signed_in_reader_gets_the_same_summary(anonymous: tuple[TestClient, list[int]]) -> None:
    client, _loads = anonymous
    researcher = User(id=uuid.UUID(int=3), name="Ravi", email="ravi@example.org", role="RESEARCHER")
    sign_in_as(client.app, lambda: researcher)
    assert client.get(PATH).json() == json.loads(golden_text(SUMMARY_GOLDEN))
