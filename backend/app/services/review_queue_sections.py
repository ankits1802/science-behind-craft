from __future__ import annotations

import uuid
from collections.abc import Iterable, Mapping, Sequence
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import Refused
from app.models import Claim, Craft, SectionProposal, User
from app.research.crafts import CraftRef
from app.research.page_proposals import PageSubject
from app.research.review_queue import SECTIONS, QueueDecision, SectionQueueItem
from app.research.review_queue_parts import RelatedFact
from app.research.review_queue_sections import ReviewedSentence, SectionReview
from app.research.section_proposals import PENDING_STATUS, SectionCheck

from .knowledge_view import craft_ref
from .monograph_generated_sections import published_section
from .open_work_subjects import WorkSubject
from .page_layouts import subject_path
from .review_queue_errors import DecisionConflict, OwnItem, UnknownItem
from .review_queue_select import Rendered, rows_by_id
from .section_gates import shown_facts, stale_problem
from .section_proposals import approve_section, reject_section, row_part, row_subject, section_owner

__all__ = ["approve_section_item", "reject_section_item", "section_items"]

DECIDED = {
    "APPROVED": (
        "Approved: the section replaces the field's published one, which is kept in the record; the page "
        "shows it after its next refresh."
    ),
    "REJECTED": "Rejected: the published section stays as it is, and the reason is kept with the proposal.",
}


async def section_items(session: AsyncSession, ids: Sequence[uuid.UUID]) -> list[Rendered]:
    rows = list(await session.scalars(select(SectionProposal).where(SectionProposal.id.in_(list(ids)))))
    crafts = await rows_by_id(session, Craft, [row.craftId for row in rows])
    rendered: list[Rendered] = []
    for row in rows:
        subject = await row_subject(session, row)
        if subject is None:
            continue
        review = await _review(session, row, subject)
        craft = crafts.get(row.craftId) if row.craftId is not None else None
        item = SectionQueueItem(
            id=row.id,
            origin=row.origin,
            submitted_at=row.createdAt,
            craft=CraftRef.model_validate(craft_ref(craft)) if craft is not None else None,
            section=review,
        )
        rendered.append(Rendered(item, row.proposerId))
    return rendered


async def approve_section_item(
    session: AsyncSession, proposal_id: uuid.UUID, reviewer: User, *, note: str | None, now: datetime
) -> QueueDecision:
    row = await _pending(session, proposal_id, reviewer)
    try:
        await approve_section(session, row, reviewer, note=note, now=now)
    except Refused as moved:
        raise DecisionConflict(moved.message) from moved
    return QueueDecision(kind=SECTIONS, id=row.id, status=row.status, message=DECIDED[row.status])


async def reject_section_item(
    session: AsyncSession, proposal_id: uuid.UUID, reviewer: User, *, reason: str, now: datetime
) -> QueueDecision:
    row = await _pending(session, proposal_id, reviewer)
    await reject_section(session, row, reviewer, reason=reason, now=now)
    return QueueDecision(kind=SECTIONS, id=row.id, status=row.status, message=DECIDED[row.status])


async def _pending(session: AsyncSession, proposal_id: uuid.UUID, reviewer: User) -> SectionProposal:
    row = await session.get(SectionProposal, proposal_id, with_for_update=True)
    if row is None:
        raise UnknownItem(f"No section proposal has the id {proposal_id}.")
    if row.proposerId == reviewer.id:
        raise OwnItem("A reviewer does not decide their own proposal.")
    if row.status != PENDING_STATUS:
        raise DecisionConflict(f"This proposal is {row.status.lower()} already. Reload the queue.")
    return row


async def _review(session: AsyncSession, row: SectionProposal, subject: WorkSubject) -> SectionReview:
    part = row_part(row)
    current = await published_section(session, section_owner(row), row.field)
    shown = list(current.sentences) if current is not None else []
    texts = await _claim_texts(session, [*row.sentences, *shown])
    return SectionReview(
        subject=PageSubject(kind=subject.kind, slug=subject.slug),
        subject_name=subject.name,
        page_url=subject_path(subject),
        field=row.field,
        proposed=_sentences(row.sentences, texts),
        published=_sentences(shown, texts),
        published_version=current.version if current is not None else None,
        note=row.note,
        task_key=row.taskKey,
        checks=[SectionCheck.model_validate(check) for check in row.checks],
        stale=stale_problem(part, await shown_facts(session, subject, part)),
    )


async def _claim_texts(session: AsyncSession, sentences: Iterable[Mapping[str, Any]]) -> dict[uuid.UUID, str]:
    wanted = list(
        dict.fromkeys(uuid.UUID(str(claim)) for s in sentences for claim in s.get("claimIds") or ())
    )
    if not wanted:
        return {}
    rows = await session.execute(select(Claim.id, Claim.text).where(Claim.id.in_(wanted)))
    return {claim_id: str(text) for claim_id, text in rows.tuples().all()}


def _sentences(
    sentences: Iterable[Mapping[str, Any]], texts: Mapping[uuid.UUID, str]
) -> list[ReviewedSentence]:
    return [
        ReviewedSentence(
            text=str(sentence["text"]),
            facts=[
                RelatedFact(id=claim, text=texts.get(claim, ""))
                for claim in (uuid.UUID(str(found)) for found in sentence.get("claimIds") or ())
            ],
        )
        for sentence in sentences
    ]
