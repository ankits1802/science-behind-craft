import json
import uuid
from collections.abc import Sequence
from typing import Any

import pytest

from app.core.errors import ExternalFailure
from app.geo.climate import ClimateTrends
from app.research.blocks import ExplainerSentence, ProseBlock
from app.research.blocks_insight import ClimateRiskBlock
from app.research.planning import PlanRequest
from app.research.sections import SectionSpec
from app.science.records import KnownClaim
from app.services import climate_risk
from app.services.answer_events import CitedClaims
from app.services.builder_interface import BuildAsk, BuilderTools
from app.services.climate_risk import ClimateRiskBuilder, climate_risk_block, meaning_statements
from app.services.knowledge_view import ClaimView

from ..contracts.phase_d_golden import phase_d, phase_d_blocks
from ..planner.fakes import FakeModel
from ..research.fixtures import AJRAKH
from .fixtures import no_session
from .season_supply_fixtures import claims_of, written_claim

CLIMATE = "s6.b1"
BLOCK_ID = "s6.climate"
CARVING = written_claim(
    "carving", "Blocks are carved from sheesham wood.", "Blocks are carved from sheesham wood."
)


def golden_climate() -> ClimateRiskBlock:
    return ClimateRiskBlock.model_validate(phase_d_blocks()[CLIMATE])


def kachchh_trends() -> ClimateTrends:
    golden = golden_climate()
    return ClimateTrends(tuple(golden.trends), tuple(golden.datasets))


def meaning_claims() -> list[KnownClaim]:
    return claims_of(
        [sentence.model_dump(mode="json", by_alias=True) for sentence in golden_climate().meaning]
    )


def view(claim: KnownClaim, *, cited: bool = True) -> ClaimView:
    citations = [c.model_dump(mode="json", by_alias=True) for c in claim.citations] if cited else []
    return ClaimView(
        id=claim.id,
        text=claim.text,
        level=claim.level,
        concept_type="CONCEPT",
        concept_id=None,
        citations=citations,
    )


def climate_ask(claims: Sequence[KnownClaim], *, uncited: frozenset[uuid.UUID] = frozenset()) -> BuildAsk:
    sentences = [
        ExplainerSentence(id=f"s6.b1.{n}", text=c.text, level=c.level, citations=list(c.citations), terms=[])
        for n, c in enumerate(claims, start=1)
    ]
    prose = ProseBlock(id="s6.b1", kind="prose", version=1, reuse=None, sentences=sentences)
    sources = {source["id"]: source for source in phase_d()["sources"]}
    cited = CitedClaims(
        views={c.id: view(c, cited=c.id not in uncited) for c in claims},
        sources={sid: sources[sid] for sid in prose.cited_source_ids() if sid in sources},
    )
    request = PlanRequest(question="Is Kutch getting drier for Ajrakh?", mode="HYBRID", craft=AJRAKH)
    spec = SectionSpec(id="s6", discipline="CLIMATE", title="Climate and risk", order=6)
    return BuildAsk(uuid.UUID(int=6), spec, request, (prose,), cited)


def meaning_model(*replies: Any) -> FakeModel:
    return FakeModel([json.dumps({"meaning": reply}) for reply in replies])


def builder(
    model: Any, monkeypatch: pytest.MonkeyPatch, trends: ClimateTrends | None = None
) -> ClimateRiskBuilder:
    async def climate(session: Any, slug: str) -> ClimateTrends:
        assert slug == AJRAKH.slug
        return kachchh_trends() if trends is None else trends

    monkeypatch.setattr(climate_risk, "craft_climate", climate)
    return ClimateRiskBuilder(
        BuilderTools(sessions=no_session, live=None, plan_model=model, compose_model=None)
    )


async def test_the_district_trends_are_paired_with_the_cited_claims_the_model_picks(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    model = meaning_model(["c1", "c2"])
    built = await builder(model, monkeypatch).build(climate_ask([CARVING, *meaning_claims()]))
    (block,) = built.blocks
    golden = golden_climate()
    assert (block.id, block.trends, block.datasets, block.groundwater) == (
        BLOCK_ID,
        golden.trends,
        golden.datasets,
        [],
    )
    assert [(s.id, s.text, s.citations) for s in block.meaning] == [
        (f"{BLOCK_ID}.{n}", s.text, s.citations) for n, s in enumerate(golden.meaning, start=1)
    ]
    assert "carved" not in model.calls[0]["user"]
    assert built.sources == {}


async def test_a_note_without_a_claim_is_dropped(monkeypatch: pytest.MonkeyPatch) -> None:
    model = meaning_model(["c9", "c2", "c2", "water levels fall", "c1"])
    built = await builder(model, monkeypatch).build(climate_ask(meaning_claims()))
    (block,) = built.blocks
    assert [s.text for s in block.meaning] == [c.text for c in reversed(meaning_claims())]


async def test_a_claim_without_citations_is_never_offered(monkeypatch: pytest.MonkeyPatch) -> None:
    water, iron = meaning_claims()
    model = meaning_model(["c1", "c2"])
    built = await builder(model, monkeypatch).build(climate_ask([water, iron], uncited=frozenset({water.id})))
    (block,) = built.blocks
    assert [s.text for s in block.meaning] == [iron.text]
    assert water.text not in model.calls[0]["user"]


async def test_a_district_without_trends_adds_no_block(monkeypatch: pytest.MonkeyPatch) -> None:
    model = meaning_model(["c1"])
    built = await builder(model, monkeypatch, ClimateTrends()).build(climate_ask(meaning_claims()))
    assert built.blocks == () and model.calls == []


async def test_trends_without_cited_meaning_are_shown_alone(monkeypatch: pytest.MonkeyPatch) -> None:
    model = meaning_model([])
    built = await builder(model, monkeypatch).build(climate_ask([CARVING]))
    (block,) = built.blocks
    assert block.meaning == [] and block.trends == golden_climate().trends
    assert model.calls == []


async def test_a_failed_choice_shows_the_trends_without_meaning(monkeypatch: pytest.MonkeyPatch) -> None:
    class Failing:
        async def __call__(self, **_: Any) -> Any:
            raise ExternalFailure("the model did not answer", service="model")

    built = await builder(Failing(), monkeypatch).build(climate_ask(meaning_claims()))
    (block,) = built.blocks
    assert block.meaning == [] and block.trends == golden_climate().trends


async def test_an_answer_without_a_craft_adds_nothing(monkeypatch: pytest.MonkeyPatch) -> None:
    ask = climate_ask(meaning_claims())
    request = PlanRequest(question=ask.request.question, mode="HYBRID", craft=None)
    no_craft = BuildAsk(ask.answer_id, ask.section, request, ask.blocks, ask.cited)
    assert (await builder(meaning_model([]), monkeypatch).build(no_craft)).blocks == ()


def test_only_statements_about_water_rain_heat_or_groundwater_are_offered() -> None:
    ask = climate_ask([CARVING, *meaning_claims()])
    offered = meaning_statements(ask.blocks, ask.cited)
    assert [claim.text for claim in offered.values()] == [c.text for c in meaning_claims()]
    assert list(offered) == ["c1", "c2"]


def test_the_block_meets_the_contract_without_meaning() -> None:
    block = climate_risk_block(kachchh_trends(), {}, ["c1"], block_id=BLOCK_ID)
    assert ClimateRiskBlock.model_validate(block.model_dump(mode="json", by_alias=True)) == block
    assert block.meaning == []
