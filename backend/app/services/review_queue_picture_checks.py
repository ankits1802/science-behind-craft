from __future__ import annotations

import uuid
from collections import defaultdict
from collections.abc import Sequence
from datetime import datetime

from pydantic import ValidationError
from sqlalchemy import exists, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Claim, MediaRef as MediaRefRow, MediaRefClaim, PictureCheck, User
from app.research.picture_checks import (
    DOES_NOT_SHOW,
    SHOWS,
    PictureCheckReview,
    StoredVerdict,
    VerdictView,
    checked_state,
    state_word,
)
from app.research.review_queue import (
    PICTURE_CHECKS,
    PictureCheckItem,
    QueueApproval,
    QueueDecision,
    QueueRejection,
)
from app.research.review_switch import AGENT

from . import audit
from .media_ref_store import stored_media_ref
from .picture_check_links import checked_link, fact_crafts, searched_link, settle_link
from .review_queue_errors import OwnItem, UnknownItem
from .review_queue_select import Rendered

__all__ = ["APPROVED", "REJECTED", "approve_check", "picture_check_items", "reject_check"]

APPROVED, REJECTED = "APPROVED", "REJECTED"
UNKNOWN = "No searched picture's link has the id {link_id}."
OWN_CHECK = "A reviewer does not decide a picture they checked themselves; another Admin decides it."
SAID = {
    APPROVED: "Approved: the picture is shown beside this fact as seen, and its checks are closed.",
    REJECTED: "Rejected: the picture is no longer shown beside this fact; the picture and its other links stay.",
}


async def approve_check(
    session: AsyncSession, item_id: uuid.UUID, reviewer: User, decision: QueueApproval, *, now: datetime
) -> QueueDecision:
    return await _ruled(session, item_id, reviewer, (True, decision.note), now=now)


async def reject_check(
    session: AsyncSession, item_id: uuid.UUID, reviewer: User, decision: QueueRejection, *, now: datetime
) -> QueueDecision:
    return await _ruled(session, item_id, reviewer, (False, decision.stated()), now=now)


async def picture_check_items(session: AsyncSession, ids: Sequence[uuid.UUID]) -> list[Rendered]:
    rows = await session.execute(
        select(MediaRefClaim, MediaRefRow, Claim.text)
        .select_from(MediaRefClaim)
        .join(MediaRefRow, MediaRefRow.id == MediaRefClaim.mediaRefId)
        .join(Claim, Claim.id == MediaRefClaim.claimId)
        .where(MediaRefClaim.id.in_(list(ids)), searched_link())
    )
    found = list(rows.tuples())
    verdicts = await _verdicts(session, [link.id for link, _, _ in found])
    crafts = await fact_crafts(session, [link.claimId for link, _, _ in found])
    rendered = []
    for link, media, fact in found:
        try:
            review = _review(link, media, fact, verdicts.get(link.id, []))
        except ValidationError:
            continue
        item = PictureCheckItem(
            id=link.id,
            origin=AGENT,
            submitted_at=link.createdAt,
            craft=crafts.get(link.claimId),
            check=review,
        )
        rendered.append(Rendered(item, None))
    return rendered


async def _ruled(
    session: AsyncSession,
    item_id: uuid.UUID,
    reviewer: User,
    ruling: tuple[bool, str | None],
    *,
    now: datetime,
) -> QueueDecision:
    shows, reason = ruling
    link = await _decided_link(session, item_id, reviewer)
    session.add(
        PictureCheck(
            linkId=link.id,
            userId=reviewer.id,
            verdict=SHOWS if shows else DOES_NOT_SHOW,
            reason=reason,
            ruling=True,
            trusted=True,
            createdAt=now,
        )
    )
    await session.flush()
    state = await settle_link(session, link, now=now)
    status = APPROVED if shows else REJECTED
    await audit.record(
        session,
        action=f"review.picture_check_{status.lower()}",
        actor=reviewer,
        target_type="MediaRefClaim",
        target_id=link.id,
        detail={"to": state_word(state), "claimId": str(link.claimId), "mediaRefId": str(link.mediaRefId)},
    )
    return QueueDecision(kind=PICTURE_CHECKS, id=link.id, status=status, message=SAID[status])


async def _decided_link(session: AsyncSession, item_id: uuid.UUID, reviewer: User) -> MediaRefClaim:
    link = await checked_link(session, item_id)
    if link is None:
        raise UnknownItem(UNKNOWN.format(link_id=item_id))
    own = exists().where(
        PictureCheck.linkId == link.id, PictureCheck.userId == reviewer.id, PictureCheck.ruling.is_(False)
    )
    if await session.scalar(select(own)):
        raise OwnItem(OWN_CHECK)
    return link


async def _verdicts(
    session: AsyncSession, link_ids: Sequence[uuid.UUID]
) -> dict[uuid.UUID, list[tuple[PictureCheck, str | None]]]:
    if not link_ids:
        return {}
    rows = await session.execute(
        select(PictureCheck, User.name)
        .outerjoin(User, User.id == PictureCheck.userId)
        .where(PictureCheck.linkId.in_(list(link_ids)))
        .order_by(PictureCheck.createdAt, PictureCheck.id)
    )
    found: dict[uuid.UUID, list[tuple[PictureCheck, str | None]]] = defaultdict(list)
    for check, name in rows.tuples():
        found[check.linkId].append((check, name))
    return found


def _review(
    link: MediaRefClaim, media: MediaRefRow, fact: str, verdicts: Sequence[tuple[PictureCheck, str | None]]
) -> PictureCheckReview:
    stored = [
        StoredVerdict(
            user_id=check.userId, shows=check.verdict == SHOWS, trusted=check.trusted, ruling=check.ruling
        )
        for check, _ in verdicts
    ]
    return PictureCheckReview(
        media=stored_media_ref(media),
        fact_id=link.claimId,
        fact=fact,
        state=state_word(checked_state(stored)),
        verdicts=[
            VerdictView(
                verdict=check.verdict,
                reason=check.reason,
                by=name,
                ruling=check.ruling,
                trusted=check.trusted,
                at=check.createdAt,
            )
            for check, name in verdicts
        ],
    )
