from __future__ import annotations

import json
import uuid
from collections.abc import AsyncIterator, Mapping, Sequence
from contextlib import asynccontextmanager
from typing import Any

from app.geo.river_trace import DistrictHit, ReachLink, districts_in_path_order, river_trace, traced_reach_ids
from app.research.blocks import ExplainerSentence, ProseBlock
from app.research.blocks_place import DistrictRef
from app.research.datasets import DatasetRef
from app.research.planning import PlanRequest
from app.research.rivers import RiverTrace
from app.research.sections import SectionSpec
from app.services.answer_events import CitedClaims
from app.services.builder_interface import BuildAsk, BuilderTools
from app.services.knowledge_view import ClaimView
from app.services.region_story import LayerOffer, OfferedRiver, RegionOffer

from ..contracts.phase_b_golden import phase_b, phase_b_blocks
from ..planner.fakes import FakeModel
from ..research.fixtures import AJRAKH

KACHCHH = 449
HEADWATER, MIDDLE, OUTLET, SIDE = 1, 2, 3, 4
STORY = "s1.b1"
LAYER = "s2.b1"
GOLDEN_REPLY = {
    "river": "r1",
    "steps": [{"claim": f"c{n}", "district": f"d{KACHCHH}"} for n in range(1, 5)],
    "layers": ["river-density"],
}


def golden_story() -> dict[str, Any]:
    return phase_b_blocks()[STORY]


def golden_layer() -> dict[str, Any]:
    return phase_b_blocks()[LAYER]


def dataset_rows() -> dict[str, DatasetRef]:
    rows = [*golden_story()["datasets"], *golden_layer()["datasets"]]
    return {row["code"]: DatasetRef.model_validate(row) for row in rows}


def fixture_reaches() -> dict[int, ReachLink]:
    reaches = [
        ReachLink(hyriv_id=HEADWATER, next_down=MIDDLE, main_riv=OUTLET, upland_skm=120.0),
        ReachLink(hyriv_id=MIDDLE, next_down=OUTLET, main_riv=OUTLET, upland_skm=260.0),
        ReachLink(hyriv_id=SIDE, next_down=OUTLET, main_riv=OUTLET, upland_skm=150.0),
        ReachLink(hyriv_id=OUTLET, next_down=0, main_riv=OUTLET, upland_skm=410.0),
    ]
    return {reach.hyriv_id: reach for reach in reaches}


def kachchh_trace() -> RiverTrace:
    links = fixture_reaches()
    path = traced_reach_ids(OUTLET, links)
    hits = [DistrictHit(position=position, district_lgd=KACHCHH, entry=0.25) for position in (2, 3)]
    return river_trace(path, links, districts_in_path_order(hits))


def kachchh_ref() -> DistrictRef:
    return DistrictRef.model_validate(golden_story()["districts"][0])


def kachchh_offer(*, datasets: Mapping[str, DatasetRef] | None = None) -> RegionOffer:
    return RegionOffer(
        craft_districts=(KACHCHH,),
        rivers=(OfferedRiver("r1", kachchh_trace(), 3, 1.2),),
        districts={KACHCHH: kachchh_ref()},
        layers=(
            LayerOffer("soil-ph-0-5cm", "Soil pH, 0-5 cm", "SOILGRIDS_2_0"),
            LayerOffer("river-density", "River density", "HYDRORIVERS_1_0"),
        ),
        datasets=dataset_rows() if datasets is None else datasets,
    )


def step_sentences() -> list[dict[str, Any]]:
    return [step["sentence"] for step in golden_story()["steps"]]


def water_views() -> list[ClaimView]:
    return [
        ClaimView(
            id=uuid.UUID(sentence["citations"][0]["claimId"]),
            text=sentence["text"],
            level=sentence["level"],
            concept_type="PLACE",
            concept_id=None,
            citations=sentence["citations"],
        )
        for sentence in step_sentences()
    ]


def water_prose(section_id: str = "s1") -> ProseBlock:
    sentences = [
        ExplainerSentence.model_validate({**sentence, "id": f"{section_id}.b1.{n}"})
        for n, sentence in enumerate(step_sentences(), start=1)
    ]
    return ProseBlock(id=f"{section_id}.b1", kind="prose", version=1, reuse=None, sentences=sentences)


def cited_water() -> CitedClaims:
    sources = {source["id"]: source for source in phase_b()["sources"]}
    prose = water_prose()
    return CitedClaims(
        views={view.id: view for view in water_views()},
        sources={source_id: sources[source_id] for source_id in prose.cited_source_ids()},
    )


def place_ask(discipline: str = "GEOGRAPHY", *, craft: bool = True, section_id: str = "s1") -> BuildAsk:
    request = PlanRequest(
        question="Why does water matter for Ajrakh in Kutch?", mode="HYBRID", craft=AJRAKH if craft else None
    )
    spec = SectionSpec(id=section_id, discipline=discipline, title="Geography and water", order=1)
    return BuildAsk(uuid.UUID(int=1), spec, request, (water_prose(section_id),), cited_water())


@asynccontextmanager
async def no_session() -> AsyncIterator[None]:
    yield None


def story_model(*replies: Mapping[str, Any]) -> FakeModel:
    return FakeModel([json.dumps(reply) for reply in replies or (GOLDEN_REPLY,)])


def place_tools(model: FakeModel | None = None) -> BuilderTools:
    return BuilderTools(sessions=no_session, live=None, plan_model=model or story_model(), compose_model=None)


def expected_story(block_id: str, **changes: Any) -> dict[str, Any]:
    story = golden_story()
    steps = [
        {**step, "sentence": {**step["sentence"], "id": f"{block_id}.{n}"}}
        for n, step in enumerate(story["steps"], start=1)
    ]
    return {**story, "id": block_id, "river": {**story["river"], "name": None}, "steps": steps, **changes}


def codes(rows: Sequence[Any]) -> list[str]:
    return [row.code for row in rows]
