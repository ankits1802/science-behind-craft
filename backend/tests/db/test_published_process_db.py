from collections.abc import AsyncIterator

import pytest
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.mcp_published_read import read_published
from app.api.mcp_review_arguments import PublishedArguments
from app.api.mcp_tool_base import ToolContext
from app.models import (
    AuditLog,
    ConditionReading,
    ImageContribution,
    MapLayerProposal,
    ProcessStage,
    StageReview,
)
from app.research.page_proposals import PageSubject
from app.research.staged_reviews import ConfirmedItem, StagedConfirmation, StagedDecision
from app.services.craft_resolver import CraftIndexStore
from app.services.open_work_subjects import craft_subject
from app.services.published_kinds import PublishedQuery
from app.services.staged_published import published_lines
from app.services.staged_review_confirm import Confirmed, confirm_batch
from app.services.staged_reviews import Staged, stage_decisions

from .published_content_seed import (
    HELD_READING,
    LATER_STAGE,
    LAYER,
    PICTURE,
    PLACED,
    PLACED_STAGE,
    READING,
    STAGE,
    WHY,
    decided,
    published_session,
)
from .review_queue_seed import NOW, SLUG, People
from .test_staged_reviews_db import caller_of

pytestmark = pytest.mark.db


@pytest.fixture
async def seeded() -> AsyncIterator[tuple[AsyncSession, People]]:
    async for opened in published_session():
        yield opened


async def stage(session: AsyncSession, people: People, *asked: StagedDecision) -> Staged:
    return await stage_decisions(session, list(asked), await caller_of(session, people.admin), now=NOW)


async def confirm(session: AsyncSession, people: People, staged: Staged) -> Confirmed:
    assert staged.batch is not None
    chosen = StagedConfirmation(
        items=[ConfirmedItem(id=item.id, action=item.action, reason=WHY) for item in staged.items]
    )
    return await confirm_batch(session, staged.batch.id, chosen, people.admin, now=NOW)


async def audited(session: AsyncSession, action: str) -> list[AuditLog]:
    return list(await session.scalars(select(AuditLog).where(AuditLog.action == action)))


async def stages(session: AsyncSession) -> list[tuple[str, int]]:
    rows = await session.execute(
        select(ProcessStage.name, ProcessStage.ordinal)
        .where(ProcessStage.id.in_([STAGE, PLACED_STAGE, LATER_STAGE]))
        .order_by(ProcessStage.ordinal)
    )
    return list(rows.tuples().all())


async def test_a_craft_page_lists_its_published_readings_and_placed_stages_and_the_approved_layers(
    seeded: tuple[AsyncSession, People],
) -> None:
    session, _ = seeded
    page = await craft_subject(session, SLUG)
    readings = await published_lines(session, PublishedQuery("READINGS", page))
    assert {(line.id, line.name) for line in readings} == {
        (READING, "Reading: Vat heat 30 °C, Reducing the vat"),
        (HELD_READING, "Reading: Vat heat 30 °C, Reducing the vat"),
    }
    placed = await published_lines(session, PublishedQuery("STAGES", page))
    assert [(line.id, line.name) for line in placed] == [(PLACED, "Stage: Airing, in Dyeing")]
    layers = await published_lines(session, PublishedQuery("LAYERS", None))
    assert [(line.id, line.name) for line in layers] == [
        (LAYER, "Map layer: Test mineral sites (TEST-PUBLISHED-SITES)")
    ]
    pictures = await published_lines(session, PublishedQuery("IMAGES", page, offset=1))
    assert pictures == []


async def test_a_removed_reading_leaves_its_pages_with_its_reason_kept_on_its_row(
    seeded: tuple[AsyncSession, People],
) -> None:
    session, people = seeded
    staged = await stage(session, people, decided("READINGS", READING, "remove"))
    assert [item.label for item in staged.items] == ["Remove Reading: Vat heat 30 °C, Reducing the vat"]
    status = await session.scalar(select(ConditionReading.reviewStatus).where(ConditionReading.id == READING))
    assert status is None
    confirmed = await confirm(session, people, staged)
    row = await session.get(ConditionReading, READING, populate_existing=True)
    assert row is not None and (row.reviewStatus, row.reviewNote, row.reviewedById) == (
        "REJECTED",
        WHY,
        people.admin.id,
    )
    assert SLUG in confirmed.owners.crafts
    (removed,) = await audited(session, "reading.removed")
    assert (removed.detail["from"], removed.detail["stated"]) == (None, "30 °C")
    again = await stage(session, people, decided("READINGS", READING, "remove"))
    assert [each.reason for each in again.refused] == [
        "No published readings item has this id; review_queue with published lists them by page."
    ]


async def test_a_removed_layer_is_no_longer_fit_to_ship_and_keeps_its_file_and_record(
    seeded: tuple[AsyncSession, People],
) -> None:
    session, people = seeded
    staged = await stage(session, people, decided("LAYERS", LAYER, "remove"))
    assert [item.label for item in staged.items] == [
        "Remove Map layer: Test mineral sites (TEST-PUBLISHED-SITES)"
    ]
    confirmed = await confirm(session, people, staged)
    row = await session.get(MapLayerProposal, LAYER, populate_existing=True)
    assert row is not None and (row.status, row.reviewNote, row.sha256) == ("REJECTED", WHY, "b" * 64)
    assert confirmed.owners.empty
    assert staged.items[0].outcome is not None and "tools/maplayers" in staged.items[0].outcome


async def test_a_placed_stage_is_refused_while_it_holds_a_picture_then_leaves_its_process_closing_up(
    seeded: tuple[AsyncSession, People],
) -> None:
    session, people = seeded
    await session.execute(
        update(ImageContribution).where(ImageContribution.id == PICTURE).values(stageId=PLACED_STAGE)
    )
    held = await stage(session, people, decided("STAGES", PLACED, "remove"))
    assert [each.reason for each in held.refused] == [
        "Airing still holds 1 picture, which would go with it: remove or move them first, then stage its removal "
        "anew."
    ]
    await session.execute(
        update(ImageContribution).where(ImageContribution.id == PICTURE).values(stageId=None)
    )
    staged = await stage(session, people, decided("STAGES", PLACED, "remove"))
    assert [item.label for item in staged.items] == ["Remove Stage: Airing, in Dyeing"]
    assert await stages(session) == [("Reducing the vat", 1), ("Airing", 2), ("Washing", 3)]
    confirmed = await confirm(session, people, staged)
    assert await stages(session) == [("Reducing the vat", 1), ("Washing", 2)]
    review = await session.get(StageReview, PLACED, populate_existing=True)
    assert review is not None and (review.status, review.note, review.processStageId) == (
        "REJECTED",
        WHY,
        None,
    )
    assert SLUG in confirmed.owners.crafts
    (removed,) = await audited(session, "stage.removed")
    assert (removed.detail["name"], removed.detail["ordinal"], removed.detail["reason"]) == ("Airing", 2, WHY)


async def test_review_queue_lists_a_page_s_published_items_and_opens_one_with_its_fields(
    seeded: tuple[AsyncSession, People],
) -> None:
    session, people = seeded
    context = ToolContext(
        session=session,
        index=CraftIndexStore(),
        site="https://kalavigyan.example",
        user=people.admin,
        scopes=frozenset({"read", "review"}),
    )
    page = PageSubject(kind="craft", slug=SLUG)
    listed = await read_published(context, PublishedArguments(kind="IMAGES", subject=page))
    assert [(item.id, item.label) for item in listed.items] == [
        (PICTURE, "Picture: The vat turns yellow-green")
    ]
    assert listed.next_cursor is None and listed.item is None
    opened = await read_published(context, PublishedArguments(kind="IMAGES", id=PICTURE))
    assert opened.item is not None and opened.item.fields == {
        "caption": "The vat turns yellow-green",
        "alt_text": "A clay vat of yellow-green liquid",
        "focal": None,
        "place": {"stage_id": None, "material_id": None, "slot": None, "task_key": None},
    }
    removed_only = await read_published(context, PublishedArguments(kind="STAGES", id=PLACED))
    assert removed_only.item is not None and (removed_only.item.label, removed_only.item.fields) == (
        "Stage: Airing, in Dyeing",
        {},
    )
