import uuid
from collections.abc import AsyncIterator

import pytest
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_engine
from app.core.shielded import ShieldedWork
from app.models import Answer, Compound, KnowledgePiece as PieceRow, Reaction
from app.research.blocks_matter import MaterialCardBlock
from app.research.crafts import CraftRef
from app.science.reaction_player import reaction_player
from app.services import knowledge_view
from app.services.claim_seed import seed_id
from app.services.craft_matter import craft_matter
from app.services.craft_process import process_records
from app.services.molecule_conformers import stored_compound_cid
from app.services.piece_lookup import PieceAsk
from app.services.piece_store import BuiltSection, SqlPieceStore

from .test_knowledge_pieces_db import WATER_CLAIMS, fixed_embedder, prose_of

pytestmark = pytest.mark.db

AJRAKH = CraftRef(slug="Kutch-Ajrakh", name="Kutch Ajrakh", path="/crafts/Kutch-Ajrakh")
QUESTION = "What does alum do in Ajrakh?"
ALUM_MATERIAL = seed_id("material", "ie:ajrakh.material.alum")
POTASSIUM_ALUM = seed_id("compound", "potassium-alum")
ALIZARIN = seed_id("compound", "alizarin")


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


def sessions_of(session: AsyncSession):
    def sessions() -> AsyncSession:
        return AsyncSession(bind=session.bind, expire_on_commit=False, autoflush=False)

    return sessions


def store_for(session: AsyncSession) -> SqlPieceStore:
    return SqlPieceStore(sessions_of(session), embed=fixed_embedder, shield=ShieldedWork())


async def answer_row(session: AsyncSession) -> uuid.UUID:
    craft = await knowledge_view.resolve_craft(session, AJRAKH.slug)
    answer_id = uuid.uuid4()
    session.add(Answer(id=answer_id, userId=None, question=QUESTION, mode="DEEP", craftId=craft.id))
    await session.flush()
    return answer_id


async def card(session: AsyncSession, block_id: str, name: str) -> MaterialCardBlock:
    prose = await prose_of(session, WATER_CLAIMS[:1])
    facts = [sentence.model_copy(update={"id": f"{block_id}.1"}) for sentence in prose.sentences]
    return MaterialCardBlock(
        id=block_id,
        kind="material_card",
        version=1,
        reuse=None,
        material_id=None,
        compound_id=None,
        term_key=None,
        name=name,
        material_kind=None,
        role=None,
        formula=None,
        pubchem_cid=None,
        wikidata_id=None,
        local_names=[],
        facts=facts,
        handling=[],
    )


async def keep_cards(session: AsyncSession, store: SqlPieceStore, *names: str) -> list[PieceRow]:
    lookup = await store.reusable(PieceAsk(QUESTION, AJRAKH, ("CHEMISTRY",), "EXPERT", fresh=True))
    answer_id = await answer_row(session)
    cards = tuple([await card(session, f"s1.b{n}", name) for n, name in enumerate(names, 1)])
    await store.keep(lookup, answer_id=answer_id, depth="EXPERT", sections=[BuiltSection("CHEMISTRY", cards)])
    rows = (await session.scalars(select(PieceRow).where(PieceRow.createdFromAnswerId == answer_id))).all()
    return list(rows)


async def test_cards_of_one_answer_never_supersede_each_other(session: AsyncSession) -> None:
    store = store_for(session)
    first = await keep_cards(session, store, "Alum", "Indigo")
    assert len(first) == 2 and all(row.supersededById is None for row in first)
    (later,) = await keep_cards(session, store, "Alum")
    for row in first:
        await session.refresh(row)
    assert [row.supersededById for row in first] == [later.id, later.id]


async def test_a_stored_reaction_player_is_reused_only_while_it_matches_the_process_rows(
    session: AsyncSession,
) -> None:
    craft = await knowledge_view.resolve_craft(session, AJRAKH.slug)
    player = reaction_player(await process_records(session, craft), block_id="s1.b1")
    assert player is not None
    assert [step.equation for step in player.steps] == [
        "Fe + 2 CH3COOH -> Fe(CH3COO)2 + H2",
        "C16H10N2O2 + 2 H^+ + 2 e^- -> C16H12N2O2",
        "2 C16H12N2O2 + O2 -> 2 C16H10N2O2 + 2 H2O",
        None,
    ]
    store = store_for(session)
    lookup = await store.reusable(PieceAsk(QUESTION, AJRAKH, ("CHEMISTRY",), "EXPERT", fresh=True))
    await store.keep(
        lookup,
        answer_id=await answer_row(session),
        depth="EXPERT",
        sections=[BuiltSection("CHEMISTRY", (player,))],
    )
    found = await store.reusable(PieceAsk(QUESTION, AJRAKH, ("CHEMISTRY",), "EXPERT"))
    assert [piece.kind for piece in found.reused["CHEMISTRY"].pieces] == ["reaction_player"]
    first = player.steps[0].reaction_id
    await session.execute(update(Reaction).where(Reaction.id == first).values(label="Iron rusting"))
    again = await store.reusable(PieceAsk(QUESTION, AJRAKH, ("CHEMISTRY",), "EXPERT"))
    assert "CHEMISTRY" not in again.reused


async def test_the_craft_s_matter_holds_the_seeded_alum_its_term_and_compound(session: AsyncSession) -> None:
    await session.execute(update(Compound).where(Compound.id == ALIZARIN).values(pubchemCid=6293))
    matter = await craft_matter(sessions_of(session), AJRAKH)
    assert matter is not None
    alum = next(material for material in matter.materials if material.material_id == ALUM_MATERIAL)
    assert alum.name == "Alum (fatakdi)" and alum.compound.id == POTASSIUM_ALUM
    assert "alum" in [term.key for term in alum.terms]
    assert {ALIZARIN, POTASSIUM_ALUM} <= set(matter.compounds)
    assert matter.compounds[ALIZARIN].pubchem_cid == 6293


async def test_only_a_stored_compound_s_cid_is_served(session: AsyncSession) -> None:
    await session.execute(update(Compound).where(Compound.id == ALIZARIN).values(pubchemCid=6293))
    assert await stored_compound_cid(session, 6293)
    assert not await stored_compound_cid(session, 999_999_999)
