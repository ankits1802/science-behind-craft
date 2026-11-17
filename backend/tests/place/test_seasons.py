import dataclasses
import uuid
from datetime import UTC, datetime
from typing import Any

import pytest

from app.geo.rainfall import MonthValue, rainfall_from
from app.research.blocks_place import DistrictRef
from app.research.knowledge_pieces import PieceSlot, knowledge_piece, piece_slot
from app.science.records import KnownClaim, StageRecord
from app.services import season_supply_builders
from app.services.block_builders import BLOCK_BUILDERS, BlockBuilders
from app.services.season_rows import SeasonFact, SeasonOffer, seasons_block
from app.services.season_supply_builders import SeasonsBuilder

from ..geo.test_rainfall import CHIRPS, KACHCHH, KACHCHH_MM, KACHCHH_REF, months
from ..science.golden_process import PA, PROCESS_ID, STAGE_CLAIMS, claim_id, golden_records, stage_id
from .season_supply_fixtures import (
    GI_JOURNAL,
    MONSOON_HUMIDITY,
    SEASONS,
    concept_of,
    golden_seasons,
    season_claims,
    season_tools,
    section_ask,
    written_claim,
)

STORED_AT = datetime(2026, 11, 17, tzinfo=UTC)
BLOCK_ID = "s3.seasons"
NEIGHBOUR = 448
NEIGHBOUR_REF = DistrictRef(district_lgd=NEIGHBOUR, name="Jamnagar", state_name="Gujarat")
PA_NAME = "Pa (alum mordant printing for red)"
KACHCHH_CLIMATE = "Kachchh climate"
JUNE_TO_SEPTEMBER = [6, 7, 8, 9]
MAPPING = written_claim(
    "monsoon-months",
    "Kachchh's rain comes with the monsoon.",
    "In Kachchh the monsoon rains fall from June to September.",
)
SLOW_DRYING = written_claim(
    "slow-drying",
    "Printed cloth dries slowly in the monsoon.",
    "printed cloth dries slowly in the monsoon",
)
OILED_BLOCKS = written_claim(
    "oiled-blocks",
    "Blocks are soaked in mustard oil when not in use so they do not expand in the rainy season.",
    "Blocks are soaked in mustard oil when not in use so they do not expand in the rainy season.",
)
DRYING_STAGE = uuid.uuid5(uuid.NAMESPACE_URL, "test-seasons/Drying in the sun")
DRYING = written_claim(
    "drying",
    "Printed cloth is dried in the sun from October to March.",
    "Printed cloth is dried in the open sun through the dry months.",
)


@pytest.fixture
def stored(monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    found: dict[str, Any] = {
        "records": golden_records(),
        "districts": (KACHCHH,),
        "rain": {KACHCHH: months(KACHCHH_MM)},
        "names": {KACHCHH: KACHCHH_REF, NEIGHBOUR: NEIGHBOUR_REF},
    }

    async def resolve(session: Any, slug: str) -> Any:
        return object()

    async def records(session: Any, craft: Any) -> Any:
        return found["records"]

    async def districts(session: Any, craft: Any) -> tuple[int, ...]:
        return found["districts"]

    async def refs(session: Any, lgds: Any) -> dict[int, DistrictRef]:
        return {lgd: found["names"][lgd] for lgd in lgds if lgd in found["names"]}

    async def rainfall(session: Any, district: DistrictRef) -> Any:
        return rainfall_from(district, CHIRPS, found["rain"].get(district.district_lgd, []))

    async def names(session: Any, concept_ids: Any) -> dict[uuid.UUID, str]:
        humidity = {concept_of(claim) for claim in season_claims()}
        return {cid: MONSOON_HUMIDITY if cid in humidity else KACHCHH_CLIMATE for cid in concept_ids}

    for name, fake in (
        ("resolve_craft", resolve),
        ("process_records", records),
        ("mapped_districts", districts),
        ("district_refs", refs),
        ("district_rainfall", rainfall),
        ("_concept_names", names),
    ):
        monkeypatch.setattr(season_supply_builders, name, fake)
    return found


def pa_claim() -> KnownClaim:
    return golden_records().claims[claim_id(STAGE_CLAIMS[PA])]


def with_stage(name: str, ordinal: int, claim: KnownClaim) -> Any:
    records = golden_records()
    stage_key = uuid.uuid5(uuid.NAMESPACE_URL, f"test-seasons/{name}")
    stage = StageRecord(stage_key, PROCESS_ID, ordinal, name, "DRY", (claim.id,))
    return dataclasses.replace(
        records, stages=(*records.stages, stage), claims={**records.claims, claim.id: claim}
    )


def shown(block: Any) -> list[tuple[str, Any, list[int], Any]]:
    return [(row.label, row.stage_id, row.months, row.season) for row in block.rows]


async def build(claims: list[KnownClaim]) -> Any:
    built = await SeasonsBuilder(season_tools()).build(section_ask(claims))
    return built.blocks[0] if built.blocks else None


def test_the_fixture_s_seasons_are_its_monsoon_claim_with_no_month() -> None:
    facts = tuple(SeasonFact(claim, MONSOON_HUMIDITY) for claim in season_claims())
    block = seasons_block(SeasonOffer(stages=(), facts=facts, rainfall=None), block_id=SEASONS)
    assert block is not None
    assert block.model_dump(mode="json", by_alias=True) == golden_seasons()


async def test_a_stage_without_a_dated_claim_gets_no_month(stored: dict[str, Any]) -> None:
    block = await build([pa_claim(), season_claims()[0]])
    assert shown(block) == [
        (PA_NAME, stage_id(PA), [], None),
        (MONSOON_HUMIDITY, None, [], "MONSOON"),
    ]
    assert block.rows[0].sentence.text == pa_claim().text


async def test_a_dated_stage_is_placed_on_the_months_its_claim_names(stored: dict[str, Any]) -> None:
    stored["records"] = with_stage("Drying in the sun", 7, DRYING)
    built = await SeasonsBuilder(season_tools()).build(section_ask([pa_claim(), season_claims()[0]]))
    (block,) = built.blocks
    assert shown(block) == [
        (PA_NAME, stage_id(PA), [], None),
        ("Drying in the sun", DRYING_STAGE, [1, 2, 3, 10, 11, 12], None),
        (MONSOON_HUMIDITY, None, [], "MONSOON"),
    ]


async def test_a_season_name_maps_to_months_only_through_a_cited_mapping(stored: dict[str, Any]) -> None:
    (humidity,) = season_claims()
    block = await build([humidity, SLOW_DRYING, MAPPING])
    assert [(row.label, row.season, row.months) for row in block.rows] == [
        (MONSOON_HUMIDITY, "MONSOON", JUNE_TO_SEPTEMBER),
        (KACHCHH_CLIMATE, "MONSOON", JUNE_TO_SEPTEMBER),
        (KACHCHH_CLIMATE, "MONSOON", JUNE_TO_SEPTEMBER),
    ]
    mapped = block.rows[0].sentence
    assert [c.claim_id for c in mapped.citations] == [str(humidity.id), str(MAPPING.id)]
    assert mapped.citations[1].quote == MAPPING.citations[0].quote
    assert mapped.text == humidity.text
    unmapped = await build([humidity, SLOW_DRYING])
    assert [(row.season, row.months) for row in unmapped.rows] == [("MONSOON", []), ("MONSOON", [])]


async def test_a_season_its_clause_rules_out_places_no_row(stored: dict[str, Any]) -> None:
    (humidity,) = season_claims()
    block = await build([humidity, OILED_BLOCKS, MAPPING])
    assert [row.sentence.text for row in block.rows] == [humidity.text, MAPPING.text]


async def test_a_mapping_stated_only_in_a_claim_s_text_maps_nothing(stored: dict[str, Any]) -> None:
    stated = written_claim(
        "monsoon-text", "The monsoon lasts from June to September.", "Rain comes mid-year."
    )
    humidity = season_claims()[0]
    block = await build([humidity, stated])
    assert [(row.sentence.text, row.months) for row in block.rows] == [
        (humidity.text, []),
        (stated.text, JUNE_TO_SEPTEMBER),
    ]


async def test_two_sources_that_disagree_on_a_season_s_months_map_nothing(stored: dict[str, Any]) -> None:
    other = written_claim(
        "monsoon-later",
        "Humid months follow the rains.",
        "The monsoon months of July to September are humid.",
    )
    block = await build([season_claims()[0], MAPPING, other])
    assert [row.months for row in block.rows] == [[], [], []]


async def test_a_date_is_not_a_month_of_the_year(stored: dict[str, Any]) -> None:
    dated = written_claim(
        "gi", "The application was advertised in December 2023.", "advertised December 19, 2023"
    )
    assert await build([dated]) is None


async def test_rainfall_is_the_first_craft_district_with_twelve_normals(stored: dict[str, Any]) -> None:
    stored["districts"] = (NEIGHBOUR, KACHCHH)
    stored["rain"] = {NEIGHBOUR: months(KACHCHH_MM)[:11], KACHCHH: months(KACHCHH_MM)}
    block = await build([season_claims()[0]])
    assert block.rainfall.model_dump(by_alias=True) == {
        "district": {"districtLgd": KACHCHH, "name": "Kachchh", "stateName": "Gujarat"},
        "datasetCode": "CHIRPS_3_0",
        "period": "2016-2025",
        "millimetres": KACHCHH_MM,
    }
    (dataset,) = block.datasets
    assert (dataset.code, dataset.period, dataset.native_resolution) == (
        "CHIRPS_3_0",
        "2016-2025",
        "0.05 degree",
    )


async def test_a_district_without_a_register_row_gives_no_rainfall(stored: dict[str, Any]) -> None:
    stored["districts"] = (NEIGHBOUR, KACHCHH)
    stored["rain"] = {NEIGHBOUR: months(KACHCHH_MM), KACHCHH: months(KACHCHH_MM)}
    stored["names"] = {KACHCHH: KACHCHH_REF}
    block = await build([season_claims()[0]])
    assert block.rainfall.district == KACHCHH_REF


async def test_missing_monthly_data_drops_the_rainfall_row(stored: dict[str, Any]) -> None:
    gap = months(KACHCHH_MM)
    gap[6] = MonthValue(depth_or_period=gap[6].depth_or_period, value=None, unit="mm/month")
    stored["rain"] = {KACHCHH: gap}
    block = await build([season_claims()[0]])
    assert (block.rainfall, block.datasets) == (None, [])
    assert shown(block) == [(MONSOON_HUMIDITY, None, [], "MONSOON")]


async def test_no_timed_row_and_no_craft_build_nothing(stored: dict[str, Any]) -> None:
    assert await build([pa_claim()]) is None
    built = await SeasonsBuilder(season_tools()).build(section_ask(season_claims(), craft=False))
    assert built.blocks == ()


async def test_the_registry_adds_the_seasons_block_with_the_sources_it_cites(stored: dict[str, Any]) -> None:
    stored["records"] = with_stage("Drying in the sun", 7, DRYING)
    (entry,) = [entry for entry in BLOCK_BUILDERS if entry.kind == "seasons"]
    ask = section_ask([season_claims()[0]])
    added = await BlockBuilders([(entry, entry.make(season_tools()))]).added(ask)
    (block,) = added.blocks
    assert (block.kind, block.id) == ("seasons", BLOCK_ID)
    assert set(block.cited_source_ids()) <= {*ask.cited.sources, *added.sources}
    assert GI_JOURNAL in added.sources


async def test_a_mapped_seasons_block_is_kept_as_a_piece_resting_on_both_claims(
    stored: dict[str, Any],
) -> None:
    (humidity,) = season_claims()
    block = await build([humidity, SLOW_DRYING, MAPPING])
    slot = PieceSlot(uuid.UUID(int=7), "CLIMATE", "climate:kutch-ajrakh", "EXPERT")
    piece = knowledge_piece(
        block, slot, piece_id=uuid.UUID(int=8), answer_id=uuid.UUID(int=9), created_at=STORED_AT
    )
    assert piece.kind == "seasons"
    assert set(piece.claim_ids) == {humidity.id, SLOW_DRYING.id, MAPPING.id}
    assert [row.months for row in piece.payload.rows] == [JUNE_TO_SEPTEMBER] * 3
    assert piece_slot(block, slot) == slot
