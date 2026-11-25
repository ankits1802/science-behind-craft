import uuid
from collections.abc import AsyncIterator
from datetime import timedelta
from io import BytesIO

import pytest
from PIL import Image
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import InvalidInput
from app.models import Answer, Claim, MediaRef as MediaRefRow, MediaRefClaim, TaskReservation, User
from app.research.image_relevance import PictureContext
from app.research.media_refs import MediaRef
from app.research.open_work import Viewer, WorkFilters
from app.research.picture_checks import IN_REVIEW, PICTURE_CHECK_TASK, SEEN, WAITING, check_key
from app.research.review_queue import QueueApproval, QueueRejection, ReviewFilters
from app.research.review_switch import AGENT
from app.services.media_ref_store import media_ref_values, media_url_key, stored_pictures
from app.services.open_work import list_open_work
from app.services.picture_check_batches import take_batch
from app.services.picture_check_links import waiting_links
from app.services.picture_check_records import CHECKED_ONCE, RULED, GivenVerdict, record_verdict
from app.services.review_queue import QueueAdapters, list_review_queue
from app.services.review_queue_decisions import ItemRef, approve_item, reject_item
from app.services.review_queue_errors import OwnItem
from app.services.served_pictures import served_picture
from app.services.trust_tiers import publishes_at_once

from .picture_seed import CONCEPT, FACT, NOW, people_in, seeded_session

pytestmark = pytest.mark.db

SECOND_FACT = uuid.UUID("1a6e0000-0000-4000-8000-0000000000f2")
WORLD = PictureContext(frozenset({"indigo"}))
SITE = "https://kalavigyan.example"
THUMBS = "https://thumb.wikimedia.org/wikipedia/commons/thumb/"
WITHIN = ("PICTURE_CHECKS",)
LOOKED = "A clay vat of indigo turning yellow-green as it is reduced"
OTHER_LOOK = "A shop's catalogue photograph of a printed sari for sale"


class Pictures:
    def __init__(self, *broken: str) -> None:
        self.broken = set(broken)
        self.asked: list[str] = []

    async def picture(self, url: str) -> bytes:
        self.asked.append(url)
        if url in self.broken:
            raise InvalidInput("the picture is gone")
        out = BytesIO()
        Image.new("RGB", (6, 4), (40, 60, 120)).save(out, format="JPEG")
        return out.getvalue()


@pytest.fixture
async def session() -> AsyncIterator[AsyncSession]:
    async for opened in seeded_session():
        opened.add(
            Claim(
                id=SECOND_FACT,
                subjectType="CONCEPT",
                subjectId=CONCEPT,
                predicate="states",
                text="Indigo is reduced in a fermenting vat before the cloth is dipped.",
                evidenceLevel="PROVISIONAL",
                origin="IMPORT",
                field="CHEMISTRY",
            )
        )
        await opened.flush()
        yield opened


async def linked(
    session: AsyncSession,
    name: str,
    *,
    provider: str = "wikimedia_commons",
    claim: uuid.UUID = FACT,
    relevance: str = "TEXT",
    image_url: str | None = None,
) -> uuid.UUID:
    image = image_url or f"{THUMBS}4/40/{name}.jpg/960px-{name}.jpg"
    page = f"https://commons.wikimedia.org/wiki/File:{name}.jpg"
    key = media_url_key(provider, page, image)
    media = MediaRef(
        id=uuid.uuid5(uuid.NAMESPACE_URL, key),
        display="INLINE",
        provider=provider,
        page_url=page,
        image_url=image,
        width=960,
        height=640,
        title=f"Indigo vat {name}",
        alt=f"An indigo vat, {name}",
        author="A. Photographer",
        site="commons.wikimedia.org",
        credit="A. Photographer, CC BY-SA 4.0",
        licence="CC BY-SA 4.0",
        licence_url=None,
        source_id=None,
        retrieved_at=NOW,
    )
    await session.execute(insert(MediaRefRow).values(media_ref_values(media, key)).on_conflict_do_nothing())
    made = await session.execute(
        insert(MediaRefClaim)
        .values(mediaRefId=media.id, claimId=claim, relevance=relevance)
        .returning(MediaRefClaim.id)
    )
    return made.scalar_one()


async def link_of(session: AsyncSession, link_id: uuid.UUID) -> MediaRefClaim:
    found = await session.scalar(
        select(MediaRefClaim).where(MediaRefClaim.id == link_id).execution_options(populate_existing=True)
    )
    assert found is not None
    return found


async def looked(
    session: AsyncSession, user: User, link_id: uuid.UUID, *, shows: bool, trusted: bool = False
) -> str | None:
    reason = LOOKED if shows else OTHER_LOOK
    given = GivenVerdict(link_id, shows, reason)
    recorded = await record_verdict(session, user, given, trusted=trusted, now=NOW)
    return recorded.check.state


async def queued(session: AsyncSession, viewer: User) -> list[uuid.UUID]:
    adapters = QueueAdapters(objects=None, turns_of=_no_turns)
    page = await list_review_queue(
        session, viewer, ReviewFilters(), adapters=adapters, now=NOW, within=WITHIN
    )
    return [item.id for item in page.items]


async def answered(session: AsyncSession, user: User, claim: uuid.UUID, *, times: int) -> None:
    session.add_all(
        [
            Answer(userId=user.id, question=f"Why is the vat green {n}?", mode="HYBRID", claimIds=[claim])
            for n in range(times)
        ]
    )
    await session.flush()


async def held_keys(session: AsyncSession, user: User) -> set[str]:
    held = await session.scalars(select(TaskReservation.taskKey).where(TaskReservation.userId == user.id))
    return set(held.all())


async def _no_turns(_: object) -> object:
    raise AssertionError("no testimony is read")


async def test_a_batch_holds_only_searched_links_waiting_for_a_look_most_served_first(
    session: AsyncSession,
) -> None:
    people = await people_in(session)
    rare = await linked(session, "Rare")
    cited = await linked(session, "Cited", claim=SECOND_FACT)
    never = {
        await linked(session, "Curated", provider="curation"),
        await linked(session, "Field", provider="field_repository"),
        await linked(session, "Seen", relevance="VISION"),
        await linked(session, "Shop", provider="searxng", image_url="https://itokri.com/products/sari.jpg"),
    }
    await answered(session, people.researcher, SECOND_FACT, times=2)
    pictures = Pictures()
    batch = await take_batch(session, people.researcher, take=5, source=pictures, now=NOW)
    shown = [each.item for each in batch.shown]
    assert [item.link_id for item in shown if item.link_id in {cited, rare}] == [cited, rare]
    assert never.isdisjoint(item.link_id for item in shown)
    assert [item.served for item in shown if item.link_id in {cited, rare}] == [2, 0]
    first = next(item for item in shown if item.link_id == cited)
    assert first.craft is not None and first.fact.startswith("Indigo is reduced")
    assert (
        "https://upload.wikimedia.org/wikipedia/commons/thumb/4/40/Cited.jpg/330px-Cited.jpg"
        in pictures.asked
    )
    assert {check_key(cited), check_key(rare)} <= await held_keys(session, people.researcher)
    other = await take_batch(session, people.other_researcher, take=5, source=Pictures(), now=NOW)
    assert {cited, rare}.isdisjoint(each.item.link_id for each in other.shown)


async def test_a_picture_that_cannot_be_fetched_is_skipped_and_never_reserved(session: AsyncSession) -> None:
    people = await people_in(session)
    gone = await linked(session, "Gone")
    kept = await linked(session, "Kept")
    broken = "https://upload.wikimedia.org/wikipedia/commons/thumb/4/40/Gone.jpg/330px-Gone.jpg"
    batch = await take_batch(session, people.researcher, take=5, source=Pictures(broken), now=NOW)
    shown = {each.item.link_id for each in batch.shown}
    assert (kept in shown, gone in shown, batch.skipped) == (True, False, 1)
    reserved = await session.scalar(select(TaskReservation).where(TaskReservation.taskKey == check_key(gone)))
    assert reserved is None


async def test_a_refusal_hides_the_link_at_once_and_leaves_the_picture_s_other_links(
    session: AsyncSession,
) -> None:
    people = await people_in(session)
    refused = await linked(session, "Shared")
    other = await linked(session, "Shared", claim=SECOND_FACT)
    assert await looked(session, people.researcher, refused, shows=False) == "HIDDEN"
    assert (await link_of(session, refused)).refusedAt == NOW
    stored = {picture.claim_id: picture for picture in await stored_pictures(session, [FACT, SECOND_FACT])}
    assert stored[FACT].refused and not served_picture(stored[FACT], WORLD)
    assert not stored[SECOND_FACT].refused and served_picture(stored[SECOND_FACT], WORLD)
    assert (await link_of(session, other)).refusedAt is None


async def test_a_shows_from_an_untrusted_account_waits_and_a_second_agreeing_one_marks_vision(
    session: AsyncSession,
) -> None:
    people = await people_in(session)
    assert not await publishes_at_once(session, people.researcher.id, AGENT)
    assert await publishes_at_once(session, people.professor.id, AGENT)
    waited = await linked(session, "Waited")
    assert await looked(session, people.researcher, waited, shows=True) == WAITING
    assert (await link_of(session, waited)).relevance == "TEXT"
    assert await looked(session, people.other_researcher, waited, shows=True) == SEEN
    assert (await link_of(session, waited)).relevance == "VISION"
    trusted = await linked(session, "Trusted")
    assert await looked(session, people.professor, trusted, shows=True, trusted=True) == SEEN
    assert (await link_of(session, trusted)).relevance == "VISION"


async def test_disagreement_reaches_an_admin_who_reverses_any_verdict(session: AsyncSession) -> None:
    people = await people_in(session)
    disputed = await linked(session, "Disputed")
    await looked(session, people.researcher, disputed, shows=True)
    assert await queued(session, people.admin) == []
    assert await looked(session, people.other_researcher, disputed, shows=False) == IN_REVIEW
    assert await queued(session, people.admin) == [disputed]
    assert await queued(session, people.professor) == []
    ref = ItemRef("PICTURE_CHECKS", disputed)
    approved = await approve_item(
        session, ref, people.admin, QueueApproval(note="It shows the vat."), now=NOW
    )
    assert approved.status == "APPROVED" and await queued(session, people.admin) == []
    link = await link_of(session, disputed)
    assert (link.relevance, link.refusedAt) == ("VISION", None)
    later = NOW + timedelta(minutes=5)
    rejection = QueueRejection(reason="A catalogue photograph, not this craft's vat.")
    assert (await reject_item(session, ref, people.admin, rejection, now=later)).status == "REJECTED"
    assert (await link_of(session, disputed)).refusedAt == later
    with pytest.raises(InvalidInput, match=RULED):
        await looked(session, people.professor, disputed, shows=True, trusted=True)


async def test_one_account_checks_a_link_once_and_never_one_another_holds(session: AsyncSession) -> None:
    people = await people_in(session)
    once = await linked(session, "Once")
    await looked(session, people.researcher, once, shows=True)
    with pytest.raises(InvalidInput, match=CHECKED_ONCE):
        await looked(session, people.researcher, once, shows=False)
    held = await linked(session, "Held")
    session.add(
        TaskReservation(
            taskKey=check_key(held),
            userId=people.other_researcher.id,
            reservedAt=NOW,
            expiresAt=NOW + timedelta(hours=2),
        )
    )
    await session.flush()
    with pytest.raises(InvalidInput, match="Another account holds this link"):
        await looked(session, people.researcher, held, shows=True)


async def test_an_admin_never_rules_on_a_link_they_checked_themselves(session: AsyncSession) -> None:
    people = await people_in(session)
    own = await linked(session, "Own")
    await looked(session, people.admin, own, shows=True, trusted=True)
    with pytest.raises(OwnItem):
        await approve_item(session, ItemRef("PICTURE_CHECKS", own), people.admin, QueueApproval(), now=NOW)


async def test_open_work_lists_one_check_task_counting_the_links_waiting_for_a_look(
    session: AsyncSession,
) -> None:
    before = await waiting_links(session)
    await linked(session, "Waiting")
    await linked(session, "Curated_pick", provider="curation")
    filters = WorkFilters(kind=PICTURE_CHECK_TASK)
    listed = await list_open_work(session, filters, Viewer(), site=SITE, now=NOW)
    (task,) = listed.tasks
    assert (task.key, task.subject, task.count, task.priority) == (
        PICTURE_CHECK_TASK,
        None,
        before + 1,
        "HIGH",
    )
