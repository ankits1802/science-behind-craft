import json
import uuid
from collections.abc import AsyncIterator, Callable

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_engine
from app.research.blocks import ProseBlock
from app.research.blocks_play import WhatIfBlock
from app.research.planning import PlanRequest
from app.research.sections import SectionSpec
from app.services.answer_events import cited_claims
from app.services.builder_evidence import fact_sentence, known_fact
from app.services.builder_interface import BuildAsk, BuilderTools
from app.services.claim_seed import seed_id
from app.services.craft_matter import craft_matter, section_sentences
from app.services.knowledge_view import claims_by_id
from app.services.what_if_builder import WhatIfBuilder
from app.services.what_if_evidence import what_if_evidence
from app.services.what_if_offers import OfferedInput, group_concepts, named_groups, what_if_inputs

from ..planner.fakes import FakeModel
from ..what_if.fixtures import (
    ALIZARIN_CONCEPT,
    ALIZARIN_ID,
    ALIZARIN_LAKE,
    CONTRAST,
    ICI_POWDER,
    LAKE_MECHANISM,
    MADDER_CONCEPT,
    MADDER_ID,
    MADDER_ROOTS,
    MADDER_WITH_INDIGO,
    RED_STAGE,
    SHIFT,
    SYNTHESISED,
    TAPANO,
    golden_what_if,
)
from .test_matter_db import AJRAKH

pytestmark = pytest.mark.db

RED = seed_id("stage", "ie:ajrakh.process_stage.red-dyeing")
USES_MADDER = "seed-2c13d7992152d36c2218"


@pytest.fixture
async def session() -> AsyncIterator[AsyncSession]:
    async with get_engine().connect() as connection:
        transaction = await connection.begin()
        try:
            session = AsyncSession(bind=connection, expire_on_commit=False, autoflush=False)
            yield session
            await session.close()
        finally:
            await transaction.rollback()


def sessions_of(session: AsyncSession) -> Callable[[], AsyncSession]:
    def sessions() -> AsyncSession:
        return AsyncSession(bind=session.bind, expire_on_commit=False, autoflush=False)

    return sessions


def claim(key: str) -> uuid.UUID:
    return seed_id("claim", key)


async def red_ask(session: AsyncSession) -> BuildAsk:
    views, sources = await claims_by_id(session, [claim(MADDER_ROOTS), claim(SYNTHESISED)])
    facts = [known_fact(views[claim(key)]) for key in (MADDER_ROOTS, SYNTHESISED)]
    prose = ProseBlock(
        id="s2.b1",
        kind="prose",
        version=1,
        reuse=None,
        sentences=[fact_sentence(fact, f"s2.b1.{n}") for n, fact in enumerate(facts, 1) if fact is not None],
    )
    request = PlanRequest(question="Why does Ajrakh red use madder or alizarin?", mode="HYBRID", craft=AJRAKH)
    spec = SectionSpec(id="s2", discipline="PROCESS", title="Red dyeing", order=2)
    return BuildAsk(uuid.uuid4(), spec, request, (prose,), cited_claims(list(views.values()), sources))


async def red_input(session: AsyncSession) -> tuple[BuildAsk, OfferedInput]:
    ask = await red_ask(session)
    matter = await craft_matter(sessions_of(session), AJRAKH)
    assert matter is not None
    groups = named_groups(matter, section_sentences(ask.blocks))
    evidence = await what_if_evidence(sessions_of(session), group_concepts(groups))
    (red,) = [found for found in what_if_inputs(groups, matter, evidence, ask.cited) if found.stage.id == RED]
    return ask, red


async def test_the_seeded_relationships_and_own_claims_of_the_red_dyes_are_read(
    session: AsyncSession,
) -> None:
    madder, alizarin = seed_id("concept", MADDER_CONCEPT), seed_id("concept", ALIZARIN_CONCEPT)
    evidence = await what_if_evidence(sessions_of(session), [madder, alizarin])
    relations = {found.claim_id: found.relation for found in evidence.relationships}
    assert relations == {
        claim(CONTRAST): "CONTRASTS_WITH",
        claim(TAPANO): "DEPENDS_ON",
        claim(SHIFT): "ENABLES",
    }
    assert claim(USES_MADDER) not in evidence.views
    assert set(evidence.concept_claims[madder]) == {claim(MADDER_ROOTS), claim(MADDER_WITH_INDIGO)}
    assert set(evidence.concept_claims[alizarin]) == {claim(SYNTHESISED), claim(ICI_POWDER)}
    assert all(evidence.views[found].citations for found in relations)


async def test_the_red_stage_s_dyes_are_offered_with_their_stored_relationships(
    session: AsyncSession,
) -> None:
    _, red = await red_input(session)
    madder, alizarin = red.options
    assert (madder.material.material_id, alizarin.material.material_id) == (MADDER_ID, ALIZARIN_ID)
    assert [o.claim.id for o in madder.outcomes] == [
        claim(CONTRAST),
        claim(TAPANO),
        *sorted([claim(MADDER_ROOTS), claim(MADDER_WITH_INDIGO)]),
    ]
    assert [o.claim.id for o in alizarin.outcomes[:4]] == [
        claim(CONTRAST),
        claim(SHIFT),
        *sorted([claim(SYNTHESISED), claim(ICI_POWDER)]),
    ]
    reacted = {o.claim.id: o.reaction_id for o in alizarin.outcomes[4:]}
    assert reacted == {claim(RED_STAGE): ALIZARIN_LAKE, claim(LAKE_MECHANISM): ALIZARIN_LAKE}


async def test_the_builder_rebuilds_the_fixture_s_dyes_from_the_seeded_rows(session: AsyncSession) -> None:
    ask, red = await red_input(session)
    madder, alizarin = red.options
    refs = {o.claim.id: o.ref for o in (*madder.outcomes, *alizarin.outcomes)}
    reply = {
        "input": red.ref,
        "changed": "Red dye",
        "options": [
            {"option": madder.ref, "outcomes": [madder.outcomes[0].ref, madder.outcomes[1].ref]},
            {"option": alizarin.ref, "outcomes": [refs[claim(SYNTHESISED)], refs[claim(LAKE_MECHANISM)]]},
        ],
    }
    tools = BuilderTools(
        sessions_of(session), live=None, plan_model=FakeModel([json.dumps(reply)]), compose_model=None
    )
    (block,) = (await WhatIfBuilder(tools).build(ask)).blocks
    golden = WhatIfBlock.model_validate(golden_what_if())
    assert block.stage_id == golden.stage_id == RED
    for built, expected in zip(block.options, golden.options[:2], strict=True):
        assert (built.label, built.material_id) == (expected.label, expected.material_id)
        assert [o.sentence.text for o in built.outcomes] == [o.sentence.text for o in expected.outcomes]
        assert [o.reaction_id for o in built.outcomes] == [o.reaction_id for o in expected.outcomes]
