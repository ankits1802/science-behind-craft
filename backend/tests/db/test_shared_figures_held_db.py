import uuid
from collections.abc import AsyncIterator, Sequence

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import KnowledgePiece
from app.services.borrowed_placements import borrowed_problem
from app.services.monograph_generated_parts import held_rows, subject_components
from app.services.open_work_subjects import WorkSubject, subject_by_key

from .shared_figures_seed import (
    CHAIN,
    FARAWAY_SLUG,
    METAL_SLUG,
    METAL_WATER,
    MONSOON,
    NEIGHBOUR_SLUG,
    RAINFALL,
    TEXTILES_SLUG,
    VAT,
    seed,
)
from .testimony_seed import rolled_back_session

pytestmark = pytest.mark.db

EVERY_FIGURE = (CHAIN, MONSOON, RAINFALL, VAT)


@pytest.fixture
async def session() -> AsyncIterator[AsyncSession]:
    async for opened in rolled_back_session():
        await seed(opened)
        yield opened


async def figures(session: AsyncSession) -> list[KnowledgePiece]:
    rows = await session.scalars(select(KnowledgePiece).where(KnowledgePiece.label.in_(EVERY_FIGURE)))
    return sorted(rows.all(), key=lambda row: str(row.label))


async def kept(
    session: AsyncSession, subject: WorkSubject, page_claims: Sequence[uuid.UUID] = ()
) -> list[str]:
    rows = await held_rows(session, subject, await figures(session), page_claims)
    return [str(row.label) for row in rows]


async def test_a_category_draws_the_shared_figures_on_its_own_crafts_facts_by_concept_and_by_overlap(
    session: AsyncSession,
) -> None:
    textiles = await subject_by_key(session, "category", TEXTILES_SLUG)
    drawn = [component.label for component in await subject_components(session, textiles, [])]
    assert drawn == [CHAIN, VAT]


async def test_a_category_of_another_science_never_draws_a_figure_on_another_category_s_crafts(
    session: AsyncSession,
) -> None:
    metal = await subject_by_key(session, "category", METAL_SLUG)
    assert await subject_components(session, metal, [METAL_WATER]) == []
    assert await kept(session, metal, [METAL_WATER]) == []


async def test_a_craft_draws_the_shared_figure_keyed_to_its_own_place_and_no_other_borrowed_one(
    session: AsyncSession,
) -> None:
    neighbour = await subject_by_key(session, "craft", NEIGHBOUR_SLUG)
    drawn = [component.label for component in await subject_components(session, neighbour, [])]
    assert drawn == [RAINFALL]
    assert await kept(session, neighbour) == [RAINFALL]


async def test_a_sibling_craft_outside_the_figure_s_place_draws_none_of_the_borrowed_figures(
    session: AsyncSession,
) -> None:
    faraway = await subject_by_key(session, "craft", FARAWAY_SLUG)
    assert await subject_components(session, faraway, []) == []
    assert await kept(session, faraway) == []


async def test_a_draft_places_a_borrowed_figure_exactly_where_the_page_draws_it(
    session: AsyncSession,
) -> None:
    neighbour = await subject_by_key(session, "craft", NEIGHBOUR_SLUG)
    faraway = await subject_by_key(session, "craft", FARAWAY_SLUG)
    textiles = await subject_by_key(session, "category", TEXTILES_SLUG)
    metal = await subject_by_key(session, "category", METAL_SLUG)
    assert await borrowed_problem(session, neighbour, [RAINFALL]) is None
    assert await borrowed_problem(session, textiles, [CHAIN, VAT]) is None
    for subject, label in ((neighbour, VAT), (neighbour, MONSOON), (faraway, RAINFALL), (metal, CHAIN)):
        refused = await borrowed_problem(session, subject, [label])
        assert refused is not None and refused.startswith(f"{label} is borrowed from the shared library"), (
            subject.slug,
            label,
        )
