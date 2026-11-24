import uuid
from collections.abc import AsyncIterator
from typing import Any

import pytest
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AuditLog, Claim, CraftGiRecord, User
from app.research.staged_reviews import ConfirmedItem, StagedConfirmation, StagedDecision
from app.services.curated_index import IndexNativeName
from app.services.staged_review_confirm import Confirmed, confirm_batch
from app.services.staged_reviews import Staged, stage_decisions

from ..structure.pages import HELD_A, HELD_B, HELD_C, HISTORY_CONCEPT, SLUG, key
from .structure_seed import CRAFT, NOW, seeded_session, stored_page, with_page
from .test_staged_reviews_db import caller_of

pytestmark = pytest.mark.db

WHY = "The source gives this entry otherwise."
ABOUT, NEW_ABOUT = "When the river dried", "When the river near the dye houses ran dry"
GI_CLAIM = key("gi-claim")


@pytest.fixture
async def seeded() -> AsyncIterator[tuple[AsyncSession, User]]:
    async for opened, _people in seeded_session():
        admin = User(id=key("admin"), name="Admin Tester", email="admin-structure@example.org", role="ADMIN")
        opened.add(admin)
        await opened.flush()
        yield opened, admin


def decided(item: uuid.UUID, action: str, **more: Any) -> StagedDecision:
    return StagedDecision.model_validate(
        {"kind": "STRUCTURE", "id": item, "action": action, "reason": WHY, **more}
    )


async def stage(session: AsyncSession, admin: User, *asked: StagedDecision) -> Staged:
    return await stage_decisions(session, list(asked), await caller_of(session, admin), now=NOW)


async def confirm(session: AsyncSession, admin: User, staged: Staged) -> Confirmed:
    assert staged.batch is not None
    chosen = StagedConfirmation(
        items=[ConfirmedItem(id=item.id, action=item.action, reason=WHY) for item in staged.items]
    )
    return await confirm_batch(session, staged.batch.id, chosen, admin, now=NOW)


async def audited(session: AsyncSession, action: str) -> list[AuditLog]:
    return list(await session.scalars(select(AuditLog).where(AuditLog.action == action)))


async def marks(session: AsyncSession) -> set[tuple[bool, str | None]]:
    rows = await session.execute(
        select(Claim.sourcesDiffer, Claim.differsOn).where(Claim.id.in_([HELD_B, HELD_C]))
    )
    return set(rows.tuples().all())


async def test_a_native_name_removal_takes_it_off_the_page_and_keeps_it_in_the_record(
    seeded: tuple[AsyncSession, User],
) -> None:
    session, admin = seeded
    staged = await stage(session, admin, decided(HELD_A, "remove"))
    assert staged.refused == [] and [item.label for item in staged.items] == [
        "Remove Native name: Ajrakh (hi)"
    ]
    assert [name.text for name in (await stored_page(session)).native_names] == ["Ajrakh"]
    confirmed = await confirm(session, admin, staged)
    assert (await stored_page(session)).native_names == [] and SLUG in confirmed.owners.crafts
    (removed,) = await audited(session, "structure.removed")
    assert removed.actorId == admin.id
    assert (removed.detail["page"], removed.detail["entry"], removed.detail["key"]) == (
        f"craft:{SLUG}",
        "NATIVE_NAME",
        "Ajrakh",
    )
    assert removed.detail["was"] == {"text": "Ajrakh", "language": "hi", "script": "Deva"}


async def test_a_conflict_s_edit_and_removal_carry_its_facts_marks_with_it(
    seeded: tuple[AsyncSession, User],
) -> None:
    session, admin = seeded
    await session.execute(
        update(Claim).where(Claim.id.in_([HELD_B, HELD_C])).values(sourcesDiffer=True, differsOn=ABOUT)
    )
    edited = await stage(session, admin, decided(HELD_B, "edit", edit={"fields": {"about": NEW_ABOUT}}))
    assert [item.label for item in edited.items] == [f"Edit Conflict: {ABOUT}"]
    await confirm(session, admin, edited)
    assert [conflict.about for conflict in (await stored_page(session)).conflicts] == [NEW_ABOUT]
    assert await marks(session) == {(True, NEW_ABOUT)}
    (change,) = await audited(session, "structure.edited")
    assert change.detail["before"] == {"about": ABOUT}
    removed = await stage(session, admin, decided(HELD_C, "remove", entry="CONFLICT"))
    await confirm(session, admin, removed)
    assert (await stored_page(session)).conflicts == []
    assert await marks(session) == {(False, None)}


async def test_an_entry_edit_passes_its_own_rules_and_a_fact_holding_two_entries_names_one(
    seeded: tuple[AsyncSession, User],
) -> None:
    session, admin = seeded
    page = await stored_page(session)
    second = IndexNativeName(text="Ajrak", language="hi", script=None, claim_id=HELD_C)
    await with_page(session, page.model_copy(update={"native_names": [*page.native_names, second]}))
    staged = await stage(
        session,
        admin,
        decided(HELD_C, "edit", edit={"fields": {"text": "Ajrakh"}}),
        decided(HELD_C, "edit", entry="NATIVE_NAME", edit={"fields": {"text": "Ajrakh"}}),
        decided(HELD_A, "edit", edit={"fields": {"script": "Lat"}}),
    )
    several, twice, script = (each.reason for each in staged.refused)
    assert several.startswith("This fact holds up more than one entry of its page (NATIVE_NAME, CONFLICT)")
    assert twice == "the page already gives the native name Ajrakh in hi"
    assert "at least 4 characters" in script
    assert staged.items == []


async def test_a_gi_record_is_edited_through_its_own_rules_then_removed(
    seeded: tuple[AsyncSession, User],
) -> None:
    session, admin = seeded
    session.add(
        Claim(
            id=GI_CLAIM,
            subjectType="CONCEPT",
            subjectId=HISTORY_CONCEPT,
            predicate="states",
            text="The craft was registered under application number 182.",
            evidenceLevel="PROVISIONAL",
            origin="IMPORT",
            status="APPROVED",
            field="POLICY",
        )
    )
    await session.flush()
    session.add(CraftGiRecord(craftId=CRAFT, applicationNumber="182", proprietors=[], claimIds=[GI_CLAIM]))
    await session.flush()
    refused = await stage(
        session, admin, decided(GI_CLAIM, "edit", edit={"fields": {"filed_on": "10 March 2009"}})
    )
    assert refused.items == [] and "YYYY" in refused.refused[0].reason
    edited = await stage(
        session, admin, decided(GI_CLAIM, "edit", edit={"fields": {"filed_on": "2009-03-10"}})
    )
    assert [item.label for item in edited.items] == ["Edit GI record of Structure Test Craft"]
    await confirm(session, admin, edited)
    record = await session.get(CraftGiRecord, CRAFT, populate_existing=True)
    assert record is not None and (record.applicationNumber, record.filedOn) == ("182", "2009-03-10")
    removed = await stage(session, admin, decided(GI_CLAIM, "remove"))
    await confirm(session, admin, removed)
    assert await session.scalar(select(CraftGiRecord.craftId).where(CraftGiRecord.craftId == CRAFT)) is None
    (gone,) = await audited(session, "structure.removed")
    assert (
        gone.detail["was"]["application_number"] == "182" and gone.detail["was"]["filed_on"] == "2009-03-10"
    )
