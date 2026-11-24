import uuid
from collections.abc import AsyncIterator
from typing import Any

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AuditLog, KnowledgePiece
from app.research.component_specs_general_delivery import DELIVERED_KEY
from app.research.staged_reviews import ConfirmedItem, StagedConfirmation, StagedDecision
from app.services.staged_review_confirm import confirm_batch
from app.services.staged_review_views import open_batches
from app.services.staged_reviews import stage_decisions

from ..research.general_spec_fixtures import HEAD, table_units
from .component_lifecycle_seed import ADMIN, BARE_CLAIM, NOW, OWN, lifecycle_seed, person
from .page_documents_seed import CRAFT_CLAIM, CRAFT_SLUG
from .test_staged_reviews_db import caller_of
from .testimony_seed import rolled_back_session

pytestmark = pytest.mark.db

WHY = "The table names the mordant too loosely."
TITLE = "Alum mordant on cotton"


@pytest.fixture
async def session() -> AsyncIterator[AsyncSession]:
    async for opened in rolled_back_session():
        await lifecycle_seed(opened)
        yield opened


async def own_id(session: AsyncSession) -> uuid.UUID:
    found = await session.scalar(select(KnowledgePiece.id).where(KnowledgePiece.label == OWN))
    assert found is not None
    return found


def edited(piece: uuid.UUID, **fields: Any) -> StagedDecision:
    return StagedDecision.model_validate(
        {"kind": "COMPONENTS", "id": piece, "action": "edit", "reason": WHY, "edit": {"fields": fields}}
    )


async def test_a_component_edit_is_drawn_through_the_delivery_checks_and_shown_before_and_after(
    session: AsyncSession,
) -> None:
    admin = await person(session, ADMIN)
    piece = await own_id(session)
    units = {**table_units(CRAFT_CLAIM), "u0005": {"text": "Potash alum"}}
    staged = await stage_decisions(
        session, [edited(piece, title=TITLE, units=units)], await caller_of(session, admin), now=NOW
    )
    assert staged.refused == [] and [item.label for item in staged.items] == [
        f"Edit Plain alum table ({OWN})"
    ]
    (item,) = (await open_batches(session, now=NOW)).batches[0].items
    assert next((change.field, change.before, change.after) for change in item.changes) == (
        "Title",
        "Plain alum table",
        TITLE,
    )
    assert staged.batch is not None
    chosen = StagedConfirmation(items=[ConfirmedItem(id=staged.items[0].id, action="edit", reason=WHY)])
    confirmed = await confirm_batch(session, staged.batch.id, chosen, admin, now=NOW)
    row = await session.get(KnowledgePiece, piece, populate_existing=True)
    assert row is not None and row.title == TITLE
    drawn = row.payload[DELIVERED_KEY]["units"]
    assert (drawn["u0005"]["text"], drawn["u0001"]["text"]) == (
        "Potash alum",
        table_units(CRAFT_CLAIM)["u0001"]["text"],
    )
    assert CRAFT_SLUG in confirmed.owners.crafts and [change.field for change in item.changes] == [
        "Title",
        "Units",
    ]
    audit = await session.scalar(select(AuditLog).where(AuditLog.action == "component.edited"))
    assert (
        audit is not None and audit.actorId == ADMIN and audit.detail["before"]["title"] == "Plain alum table"
    )


async def test_a_component_edit_that_fails_a_delivery_check_or_cites_new_facts_is_refused_at_staging(
    session: AsyncSession,
) -> None:
    admin = await person(session, ADMIN)
    piece = await own_id(session)
    broken = {"head": HEAD, "columns": [{"label": "u0003"}]}
    borrowed = {
        **table_units(CRAFT_CLAIM),
        "u0006": {"text": "Fixes the madder red", "claimIds": [str(BARE_CLAIM)]},
    }
    staged = await stage_decisions(
        session,
        [edited(piece, spec=broken), edited(piece, units=borrowed)],
        await caller_of(session, admin),
        now=NOW,
    )
    drawn, cited = (each.reason for each in staged.refused)
    assert drawn.startswith("The component cannot be drawn as delivered")
    assert cited == (
        f"An edit cites only the facts {OWN} already rests on, and these are new: {BARE_CLAIM}. To cite other "
        f"facts, propose a replacement that names replaces {OWN}."
    )
    row = await session.get(KnowledgePiece, piece, populate_existing=True)
    assert row is not None and row.payload[DELIVERED_KEY]["units"] == table_units(CRAFT_CLAIM)
