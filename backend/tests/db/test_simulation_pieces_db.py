import uuid
from collections.abc import AsyncIterator, Sequence
from datetime import UTC, datetime
from typing import Any

import pytest
from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.db import get_engine
from app.core.shielded import ShieldedWork
from app.models import Answer, AuditLog, Claim, ClaimSource, Concept, KnowledgePiece as PieceRow, Source, User
from app.research.blocks import ProseBlock
from app.research.blocks_play import SimulationBlock
from app.research.citations import Citation
from app.research.explainer import Explainer
from app.research.simulation_draft import SimulationDraft, checked_draft, offered_values
from app.services import knowledge_view
from app.services.answer_store import EXPLAINER_PAYLOAD_KEY
from app.services.piece_lookup import PieceAsk
from app.services.piece_store import BuiltSection, SqlPieceStore, piece_id
from app.services.simulation_hiding import (
    SIMULATION_HIDDEN_ACTION,
    SIMULATION_SHOWN_ACTION,
    HiddenPiece,
    SimulationHide,
    set_simulation_hidden,
    with_hidden_marks,
)
from app.services.simulation_pieces import simulation_pieces

from ..contracts.explainer_golden import DOCUMENT, golden_json
from ..simulations.fixtures import (
    CONCEPT,
    HIGH_LABEL,
    LOW_LABEL,
    OPUS,
    TITLE,
    accepted_html,
)
from .test_knowledge_pieces_db import AJRAKH, QUESTION, fixed_embedder, prose_of

pytestmark = pytest.mark.db

NOW = datetime.now(UTC).replace(microsecond=0)
WATER_QUOTE = "the level of water has been going down by 10-15 feet every year even here"
Sessions = async_sessionmaker[AsyncSession]


@pytest.fixture
async def sessions() -> AsyncIterator[Sessions]:
    async with get_engine().connect() as connection:
        transaction = await connection.begin()
        try:
            yield async_sessionmaker(
                bind=connection, expire_on_commit=False, join_transaction_mode="create_savepoint"
            )
        finally:
            await transaction.rollback()


async def person(session: AsyncSession, role: str = "PROFESSOR") -> User:
    user = User(
        id=uuid.uuid4(), name="Hide Tester", email=f"hide-{uuid.uuid4().hex[:8]}@example.com", role=role
    )
    session.add(user)
    await session.commit()
    return user


async def water_claim(session: AsyncSession) -> uuid.UUID:
    craft = await knowledge_view.resolve_craft(session, AJRAKH.slug)
    assert craft is not None
    concept = Concept(
        id=uuid.uuid4(), craftId=craft.id, type="ENVIRONMENTAL_CONDITION", name="Falling water table"
    )
    source = Source(
        id=uuid.uuid4(), kind="WEB_PAGE", title="Running out of water", url="https://khamir.example/w"
    )
    claim = Claim(
        id=uuid.uuid4(),
        subjectType="CONCEPT",
        subjectId=concept.id,
        predicate="states",
        text="Water levels in Kutch have been going down by 10-15 feet every year.",
        evidenceLevel="PROVISIONAL",
        origin="LIVE_RESEARCH",
    )
    session.add_all([concept, source, claim])
    await session.flush()
    session.add(ClaimSource(claimId=claim.id, sourceId=source.id, quote=WATER_QUOTE))
    await session.commit()
    return claim.id


async def simulation_of(
    session: AsyncSession, claim_id: uuid.UUID, *, concept: str = CONCEPT
) -> SimulationBlock:
    views, _ = await knowledge_view.claims_by_id(session, [claim_id])
    offers = offered_values(Citation.model_validate(c) for c in views[claim_id].citations)
    values = [
        {"ref": "v1", "key": "fallLowFeet", "label": LOW_LABEL, "unit": "feet"},
        {"ref": "v2", "key": "fallHighFeet", "label": HIGH_LABEL, "unit": "feet"},
    ]
    reply = {"build": True, "concept": concept, "title": TITLE, "values": values, "html": accepted_html()}
    check = checked_draft(
        SimulationDraft.model_validate(reply), offers, block_id="s1.b2", model=OPUS, created_at=NOW
    )
    assert check.block is not None, check.problems
    return check.block


async def explainer_payload(
    session: AsyncSession, answer_id: uuid.UUID, blocks: Sequence[Any]
) -> dict[str, Any]:
    claims = {uuid.UUID(claim) for block in blocks for claim in block.cited_claim_ids()}
    _, sources = await knowledge_view.claims_by_id(session, claims)
    refs = {str(source_id): knowledge_view.source_ref(source) for source_id, source in sources.items()}
    order = dict.fromkeys(source_id for block in blocks for source_id in block.cited_source_ids())
    section = {
        "id": "s1",
        "discipline": "GEOGRAPHY",
        "title": "Geography and water",
        "order": 1,
        "state": "READY",
        "blocks": [block.model_dump(mode="json", by_alias=True) for block in blocks],
        "searched": None,
    }
    document = golden_json(DOCUMENT) | {
        "answerId": str(answer_id),
        "question": QUESTION,
        "sections": [section],
        "sources": [refs[source_id] for source_id in order],
    }
    return {EXPLAINER_PAYLOAD_KEY: Explainer.model_validate(document).model_dump(mode="json", by_alias=True)}


async def kept_answer(sessions: Sessions, asker: User) -> tuple[uuid.UUID, ProseBlock, SimulationBlock]:
    async with sessions() as session:
        claim_id = await water_claim(session)
        prose, simulation = await prose_of(session, [claim_id]), await simulation_of(session, claim_id)
        answer_id = uuid.uuid4()
        payload = await explainer_payload(session, answer_id, [prose, simulation])
        session.add(Answer(id=answer_id, userId=asker.id, question=QUESTION, mode="DEEP", payload=payload))
        await session.commit()
    store = SqlPieceStore(sessions, embed=fixed_embedder, shield=ShieldedWork())
    lookup = await store.reusable(PieceAsk(QUESTION, AJRAKH, ("GEOGRAPHY",), "EXPERT", fresh=True))
    built = BuiltSection("GEOGRAPHY", (prose, simulation))
    await store.keep(lookup, answer_id=answer_id, depth="EXPERT", sections=[built])
    return answer_id, prose, simulation


async def reused_kinds(sessions: Sessions) -> list[str]:
    store = SqlPieceStore(sessions, embed=fixed_embedder, shield=ShieldedWork())
    lookup = await store.reusable(PieceAsk(QUESTION, AJRAKH, ("GEOGRAPHY",), "EXPERT"))
    section = lookup.reused.get("GEOGRAPHY")
    return [piece.kind for piece in section.pieces] if section else []


async def test_a_kept_explainer_is_a_cross_craft_piece_reused_with_its_section(sessions: Sessions) -> None:
    async with sessions() as session:
        asker = await person(session)
    answer_id, _, simulation = await kept_answer(sessions, asker)
    async with sessions() as session:
        row = await session.get(PieceRow, piece_id(answer_id, simulation.id))
    assert row is not None
    assert (row.craftId, row.kind, row.facet, row.topicKey) == (
        None,
        "simulation",
        "GEOGRAPHY",
        "concept:falling-water-table",
    )
    assert (row.hiddenAt, row.hiddenById) == (None, None)
    assert await reused_kinds(sessions) == ["prose", "simulation"]


async def test_stored_explainers_are_found_for_claims_on_offer_and_hidden_ones_always(
    sessions: Sessions,
) -> None:
    async with sessions() as session:
        asker = await person(session)
    _, _, simulation = await kept_answer(sessions, asker)
    claims = [uuid.UUID(claim) for claim in simulation.cited_claim_ids()]
    async with sessions() as session:
        found = await simulation_pieces(session, [*claims, uuid.uuid4()], ["GEOGRAPHY"])
        assert [piece.payload.concept for piece in found] == [CONCEPT]
        assert await simulation_pieces(session, [uuid.uuid4()], ["GEOGRAPHY"]) == []
        assert await simulation_pieces(session, claims, ["CHEMISTRY"]) == []
        await session.execute(update(PieceRow).where(PieceRow.kind == "simulation").values(staleSince=NOW))
        assert await simulation_pieces(session, claims, ["GEOGRAPHY"]) == []
        await session.execute(update(PieceRow).where(PieceRow.kind == "simulation").values(hiddenAt=NOW))
        hidden = await simulation_pieces(session, claims, ["CHEMISTRY"])
        assert [(piece.payload.concept, piece.hidden_at) for piece in hidden] == [(CONCEPT, NOW)]


async def test_a_professor_hides_their_answer_s_explainer_and_it_is_never_reused(sessions: Sessions) -> None:
    async with sessions() as session:
        asker = await person(session)
    answer_id, _, simulation = await kept_answer(sessions, asker)
    kept = piece_id(answer_id, simulation.id)
    async with sessions() as session:
        marked = await set_simulation_hidden(
            session, SimulationHide(answer_id, "s1.b2", True), user=asker, now=NOW
        )
    assert marked is not None
    assert (marked.piece_id, marked.hidden) == (kept, True)
    async with sessions() as session:
        row = await session.get(PieceRow, kept)
        assert row is not None and (row.hiddenAt, row.hiddenById) == (NOW, asker.id)
        stored = await session.scalar(select(Answer.payload).where(Answer.id == answer_id))
        explainer = Explainer.model_validate(stored[EXPLAINER_PAYLOAD_KEY])
        shown = await with_hidden_marks(session, explainer)
        assert [block.hidden for block in shown.sections[0].blocks if isinstance(block, SimulationBlock)] == [
            True
        ]
        audits = await session.scalars(select(AuditLog.action).where(AuditLog.targetId == str(kept)))
        assert audits.all() == [SIMULATION_HIDDEN_ACTION]
    assert await reused_kinds(sessions) == ["prose"]


async def test_showing_again_clears_the_mark_and_a_repeat_writes_nothing(sessions: Sessions) -> None:
    async with sessions() as session:
        asker = await person(session)
    answer_id, _, simulation = await kept_answer(sessions, asker)
    kept = piece_id(answer_id, simulation.id)
    for hidden in (True, True, False, False):
        async with sessions() as session:
            await set_simulation_hidden(
                session, SimulationHide(answer_id, "s1.b2", hidden), user=asker, now=NOW
            )
    async with sessions() as session:
        row = await session.get(PieceRow, kept)
        assert row is not None and (row.hiddenAt, row.hiddenById) == (None, None)
        audits = await session.scalars(select(AuditLog.action).where(AuditLog.targetId == str(kept)))
        assert sorted(audits.all()) == sorted([SIMULATION_HIDDEN_ACTION, SIMULATION_SHOWN_ACTION])
    assert await reused_kinds(sessions) == ["prose", "simulation"]


@pytest.mark.parametrize(
    ("who", "block_id"),
    [("other", "s1.b2"), ("asker", "s1.b1"), ("asker", "s1.b9")],
    ids=["another's answer", "not a simulation", "no such block"],
)
async def test_hiding_is_refused_for_what_is_not_the_asker_s_kept_explainer(
    sessions: Sessions, who: str, block_id: str
) -> None:
    async with sessions() as session:
        asker, other = await person(session), await person(session, "ADMIN")
    answer_id, _, _ = await kept_answer(sessions, asker)
    user = other if who == "other" else asker
    async with sessions() as session:
        assert (
            await set_simulation_hidden(
                session, SimulationHide(answer_id, block_id, True), user=user, now=NOW
            )
            is None
        )


async def test_an_explainer_never_kept_as_a_piece_is_kept_hidden_when_a_professor_hides_it(
    sessions: Sessions,
) -> None:
    async with sessions() as session:
        asker = await person(session)
    answer_id, _, simulation = await kept_answer(sessions, asker)
    kept = piece_id(answer_id, simulation.id)
    async with sessions() as session:
        await session.execute(delete(PieceRow).where(PieceRow.id == kept))
        await session.commit()
        marked = await set_simulation_hidden(
            session, SimulationHide(answer_id, "s1.b2", True), user=asker, now=NOW
        )
    assert marked == HiddenPiece(kept, True)
    async with sessions() as session:
        row = await session.get(PieceRow, kept)
        assert row is not None
        assert (row.craftId, row.facet, row.topicKey, row.depth, row.createdFromAnswerId) == (
            None,
            "GEOGRAPHY",
            "concept:falling-water-table",
            "EXPERT",
            answer_id,
        )
        assert (row.hiddenAt, row.hiddenById) == (NOW, asker.id)
    assert await reused_kinds(sessions) == ["prose"]


async def test_a_block_carried_into_another_answer_hides_the_piece_its_first_answer_kept(
    sessions: Sessions,
) -> None:
    async with sessions() as session:
        asker = await person(session)
    first, prose, simulation = await kept_answer(sessions, asker)
    later = uuid.uuid4()
    async with sessions() as session:
        payload = await explainer_payload(session, later, [prose, simulation])
        session.add(Answer(id=later, userId=asker.id, question=QUESTION, mode="DEEP", payload=payload))
        await session.commit()
        marked = await set_simulation_hidden(
            session, SimulationHide(later, "s1.b2", True), user=asker, now=NOW
        )
    assert marked == HiddenPiece(piece_id(first, simulation.id), True)
    async with sessions() as session:
        assert await session.get(PieceRow, piece_id(later, simulation.id)) is None
        stored = await session.scalar(select(Answer.payload).where(Answer.id == first))
        shown = await with_hidden_marks(session, Explainer.model_validate(stored[EXPLAINER_PAYLOAD_KEY]))
        assert [block.hidden for block in shown.sections[0].blocks if isinstance(block, SimulationBlock)] == [
            True
        ]
