import uuid
from collections.abc import AsyncIterator
from datetime import timedelta
from typing import Any

import pytest
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    AuditLog,
    Chunk,
    Claim,
    ClaimSource,
    ImageContribution,
    MediaAsset,
    PageLayout,
    ReviewEvent,
    Source,
)
from app.research.page_layout import PageLayoutEntry
from app.research.staged_reviews import ConfirmedItem, StagedConfirmation, StagedDecision
from app.services.contributed_pictures import shown_contributions
from app.services.open_work_subjects import craft_subject
from app.services.page_layouts import layout_of, store_layout
from app.services.review_queue_errors import DecisionConflict, NotYourQueue
from app.services.staged_review_confirm import Confirmed, confirm_batch, discard_batch
from app.services.staged_review_views import open_batches
from app.services.staged_reviews import Staged, stage_decisions

from .published_content_seed import (
    ASSET,
    CHUNK,
    PICTURE,
    QUOTED,
    SECOND_SOURCE,
    STAGE,
    THIRD_SOURCE,
    WHY,
    decided,
    published_session,
)
from .review_queue_seed import CRAFT, LIVE, NOW, SLUG, SOURCE, People
from .test_staged_reviews_db import caller_of

pytestmark = pytest.mark.db

GOOD_TEXT = "Lime keeps the vat alkaline so the indigo stays reduced."
ALT = "A clay vat of indigo turning yellow-green"
FOCAL = {"x": 0.1, "y": 0.2, "width": 0.5, "height": 0.5}
LOOSE = {"stage_id": None, "material_id": None, "slot": None, "task_key": None}


@pytest.fixture
async def seeded() -> AsyncIterator[tuple[AsyncSession, People]]:
    async for opened in published_session():
        yield opened


async def stage(session: AsyncSession, people: People, *asked: StagedDecision) -> Staged:
    return await stage_decisions(session, list(asked), await caller_of(session, people.admin), now=NOW)


async def confirm(session: AsyncSession, people: People, staged: Staged, **when: Any) -> Confirmed:
    assert staged.batch is not None
    chosen = StagedConfirmation(
        items=[ConfirmedItem(id=item.id, action=item.action, reason=WHY) for item in staged.items]
    )
    return await confirm_batch(session, staged.batch.id, chosen, people.admin, now=when.get("now", NOW))


async def audits(session: AsyncSession, action: str) -> list[AuditLog]:
    return list(await session.scalars(select(AuditLog).where(AuditLog.action == action)))


async def shown(session: AsyncSession) -> list[uuid.UUID]:
    return list(await session.scalars(shown_contributions(CRAFT)))


async def test_a_picture_removal_changes_nothing_until_confirmed_then_keeps_its_record(
    seeded: tuple[AsyncSession, People],
) -> None:
    session, people = seeded
    staged = await stage(session, people, decided("IMAGES", PICTURE, "remove"))
    assert staged.refused == [] and [item.label for item in staged.items] == [
        "Remove Picture: The vat turns yellow-green"
    ]
    assert await shown(session) == [PICTURE] and await audits(session, "picture.removed") == []
    confirmed = await confirm(session, people, staged)
    assert [item.state for item in staged.items] == ["APPLIED"] and SLUG in confirmed.owners.crafts
    assert await shown(session) == []
    asset = await session.get(MediaAsset, ASSET, populate_existing=True)
    row = await session.get(ImageContribution, PICTURE, populate_existing=True)
    assert asset is not None and asset.visibility == "PRIVATE"
    assert row is not None and (row.status, row.caption) == ("APPROVED", "The vat turns yellow-green")
    (removed,) = await audits(session, "picture.removed")
    assert (removed.actorId, removed.detail["reason"]) == (people.admin.id, WHY)


async def test_a_picture_edit_shows_each_field_before_and_after_and_lands_on_confirmation(
    seeded: tuple[AsyncSession, People],
) -> None:
    session, people = seeded
    fields = {"altText": ALT, "focal": FOCAL, "place": {"stage_id": str(STAGE)}}
    staged = await stage(session, people, decided("IMAGES", PICTURE, "edit", edit={"fields": fields}))
    assert staged.refused == []
    stored = StagedDecision.model_validate(staged.items[0].decision)
    assert stored.edit is not None and stored.edit.before == {
        "alt_text": "A clay vat of yellow-green liquid",
        "focal": None,
        "place": LOOSE,
    }
    (item,) = (await open_batches(session, now=NOW)).batches[0].items
    assert [(change.field, change.before, change.after) for change in item.changes] == [
        ("Alt text", "A clay vat of yellow-green liquid", ALT),
        ("Focal", None, '{"height": 0.5, "width": 0.5, "x": 0.1, "y": 0.2}'),
        (
            "Place",
            '{"material_id": null, "slot": null, "stage_id": null, "task_key": null}',
            f'{{"material_id": null, "slot": null, "stage_id": "{STAGE}", "task_key": null}}',
        ),
    ]
    row = await session.get(ImageContribution, PICTURE, populate_existing=True)
    assert row is not None and (row.altText, row.focal, row.stageId) == (
        "A clay vat of yellow-green liquid",
        None,
        None,
    )
    await confirm(session, people, staged)
    row = await session.get(ImageContribution, PICTURE, populate_existing=True)
    assert row is not None and (row.altText, row.focal, row.stageId) == (ALT, FOCAL, STAGE)
    (edited,) = await audits(session, "picture.edited")
    assert (
        edited.actorId == people.admin.id
        and edited.detail["before"]["alt_text"] == "A clay vat of yellow-green liquid"
    )


async def test_a_picture_edit_that_fails_its_gates_is_refused_at_staging_in_their_words(
    seeded: tuple[AsyncSession, People],
) -> None:
    session, people = seeded
    asked = [
        {"place": {"stage_id": str(uuid.uuid4())}},
        {"focal": {"x": 0.7, "y": 0.0, "width": 0.5, "height": 0.5}},
        {"caption": "The vat turns yellow-green"},
        {"licence": "CC-BY-4.0"},
    ]
    staged = await stage(
        session, people, *(decided("IMAGES", PICTURE, "edit", edit={"fields": each}) for each in asked)
    )
    assert staged.items == [] and staged.batch is None
    reasons = [each.reason for each in staged.refused]
    assert reasons[0] == "That stage is not one of this craft's"
    assert "a focal box lies inside its picture" in reasons[1]
    assert reasons[2].startswith("An edit changes at least one field")
    assert "Extra inputs are not permitted" in reasons[3]


async def test_a_fact_edit_is_matched_against_its_quotes_then_written_with_its_audit(
    seeded: tuple[AsyncSession, People],
) -> None:
    session, people = seeded
    figures = decided(
        "FACTS", QUOTED, "edit", edit={"fields": {"text": "Lime keeps the vat alkaline for 12 days."}}
    )
    good = decided("FACTS", QUOTED, "edit", edit={"fields": {"text": GOOD_TEXT}})
    staged = await stage(session, people, figures, good)
    (refused,) = staged.refused
    assert refused.index == 0 and refused.reason.startswith(
        "The new text fails the quote check the fact passed: 12"
    )
    assert [item.label for item in staged.items] == ["Edit Fact: Lime keeps the indigo vat alkaline."]
    await confirm(session, people, staged)
    claim = await session.get(Claim, QUOTED, populate_existing=True)
    assert claim is not None and (claim.text, claim.version, claim.embedding) == (GOOD_TEXT, 2, None)
    event = await session.scalar(select(ReviewEvent).where(ReviewEvent.claimId == QUOTED))
    assert event is not None and event.note == f"Text edited: {WHY}" and event.actorId == people.admin.id
    (edited,) = await audits(session, "fact.edited")
    assert (edited.detail["before"], edited.detail["after"]) == (
        "Lime keeps the indigo vat alkaline.",
        GOOD_TEXT,
    )


async def test_a_fact_edit_is_refused_when_its_quote_left_its_passage_or_its_text_moved_meanwhile(
    seeded: tuple[AsyncSession, People],
) -> None:
    session, people = seeded
    staged = await stage(
        session, people, decided("FACTS", QUOTED, "edit", edit={"fields": {"text": GOOD_TEXT}})
    )
    await session.execute(update(Claim).where(Claim.id == QUOTED).values(text="Lime is added to the vat."))
    await confirm(session, people, staged)
    (item,) = staged.items
    await session.refresh(item)
    assert (
        item.state == "REFUSED" and item.outcome is not None and item.outcome.startswith("Text changed after")
    )
    await session.execute(
        update(Chunk).where(Chunk.id == CHUNK).values(text="The dyers stir the vat twice a day.")
    )
    again = await stage(
        session, people, decided("FACTS", QUOTED, "edit", edit={"fields": {"text": GOOD_TEXT}})
    )
    (refused,) = again.refused
    assert refused.reason.endswith("quote 1 (p. 4) is no longer in the passage stored for its source")


async def test_a_source_is_unlinked_only_where_nothing_would_be_left_resting_on_it_alone(
    seeded: tuple[AsyncSession, People],
) -> None:
    session, people = seeded
    asked = [decided("SOURCES", key, "remove") for key in (SOURCE, THIRD_SOURCE, SECOND_SOURCE)]
    staged = await stage(session, people, *asked)
    alone, read = staged.refused
    assert alone.reason.startswith("These facts cite only Indigo vats") and str(QUOTED) in alone.reason
    assert read.reason.startswith("The readings read from Vat notes's quotes (1) would go with them")
    assert [item.label for item in staged.items] == ["Remove Source: A dye house visit"]
    confirmed = await confirm(session, people, staged)
    cited = await session.scalar(select(func.count()).where(ClaimSource.sourceId == SECOND_SOURCE))
    assert cited == 0 and await session.get(Source, SECOND_SOURCE) is not None
    assert SLUG in confirmed.owners.crafts
    (removed,) = await audits(session, "source.removed")
    assert removed.detail["citations"] == [
        {"claim": str(LIVE), "quote": "lime in the vat", "locator": "visit"}
    ]
    assert (removed.detail["cited"], removed.detail["pieces"]) == (1, 0)


async def test_a_layout_removal_brings_back_the_layout_before_it_and_keeps_every_version(
    seeded: tuple[AsyncSession, People],
) -> None:
    session, people = seeded
    versions = dict(
        (await session.execute(select(PageLayout.version, PageLayout.id).where(PageLayout.craftId == CRAFT)))
        .tuples()
        .all()
    )
    staged = await stage(
        session, people, decided("LAYOUTS", versions[1], "remove"), decided("LAYOUTS", versions[2], "remove")
    )
    (stale,) = staged.refused
    assert stale.index == 0 and stale.reason.startswith("No published layouts item has this id")
    assert [item.label for item in staged.items] == [f"Remove Layout version 2 of the page of {SLUG}"]
    await confirm(session, people, staged)
    layout = await layout_of(session, await craft_subject(session, SLUG))
    assert layout is not None and (layout.version, [entry.ref for entry in layout.entries]) == (3, ["u0001"])
    (removed,) = await audits(session, "layout.removed")
    assert (removed.detail["version"], removed.detail["restored"]) == (2, 1)


async def removed_version(session: AsyncSession, people: People, version: int) -> tuple[int, list[str]]:
    layout_id = await session.scalar(
        select(PageLayout.id).where(PageLayout.craftId == CRAFT, PageLayout.version == version)
    )
    assert layout_id is not None
    staged = await stage(session, people, decided("LAYOUTS", layout_id, "remove"))
    assert staged.refused == []
    await confirm(session, people, staged)
    layout = await layout_of(session, await craft_subject(session, SLUG))
    assert layout is not None
    return layout.version, [entry.ref for entry in layout.entries]


async def test_removing_a_layout_that_was_itself_a_restore_never_brings_back_the_removed_one(
    seeded: tuple[AsyncSession, People],
) -> None:
    session, people = seeded
    assert await removed_version(session, people, 2) == (3, ["u0001"])
    assert await removed_version(session, people, 3) == (4, [])
    restored = [
        (each.detail["version"], each.detail["restored"]) for each in await audits(session, "layout.removed")
    ]
    assert sorted(restored) == [(2, 1), (3, None)]


async def test_a_removal_restores_the_latest_earlier_arrangement_no_removal_took_off(
    seeded: tuple[AsyncSession, People],
) -> None:
    session, people = seeded
    third = [PageLayoutEntry(ref="u0003", chapter="glance", order=1, role="BODY")]
    await store_layout(session, await craft_subject(session, SLUG), third, actor=people.admin)
    assert await removed_version(session, people, 3) == (4, ["u0001", "u0002"])
    assert await removed_version(session, people, 4) == (5, ["u0001"])
    assert await removed_version(session, people, 5) == (6, [])


async def test_a_discarded_or_expired_batch_leaves_published_content_as_it_was(
    seeded: tuple[AsyncSession, People],
) -> None:
    session, people = seeded
    first = await stage(session, people, decided("IMAGES", PICTURE, "remove"))
    assert first.batch is not None
    await discard_batch(session, first.batch.id, people.admin, now=NOW)
    second = await stage(
        session, people, decided("FACTS", QUOTED, "edit", edit={"fields": {"text": GOOD_TEXT}})
    )
    with pytest.raises(DecisionConflict):
        await confirm(session, people, second, now=NOW + timedelta(days=3, minutes=1))
    claim = await session.get(Claim, QUOTED, populate_existing=True)
    assert (
        await shown(session) == [PICTURE]
        and claim is not None
        and claim.text == "Lime keeps the indigo vat alkaline."
    )


async def test_only_an_admin_stages_or_confirms_a_change_to_published_content(
    seeded: tuple[AsyncSession, People],
) -> None:
    session, people = seeded
    with pytest.raises(NotYourQueue):
        await stage_decisions(
            session,
            [decided("IMAGES", PICTURE, "remove")],
            await caller_of(session, people.professor),
            now=NOW,
        )
    staged = await stage(session, people, decided("IMAGES", PICTURE, "remove"))
    assert staged.batch is not None
    chosen = StagedConfirmation(items=[ConfirmedItem(id=staged.items[0].id, action="remove", reason=WHY)])
    with pytest.raises(NotYourQueue):
        await confirm_batch(session, staged.batch.id, chosen, people.professor, now=NOW)
    assert await shown(session) == [PICTURE]
