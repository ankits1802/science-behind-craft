from __future__ import annotations

import re
import uuid
from collections.abc import Sequence
from datetime import datetime
from typing import Any

from sqlalchemy import ColumnElement, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import InvalidInput
from app.core.roles import PROFESSOR, has_rank
from app.models import ComponentProposal, Compound, Concept, Craft, KnowledgePiece, User
from app.models.knowledge_pieces import PLACE_KEY_PATTERN
from app.models.open_work import LIVE_PROPOSALS
from app.research.component_proposals import (
    SUBJECT_LINK,
    WAYS_ON,
    ComponentProposalDraft,
    ComponentProposalResult,
    close_matches,
    proposal_crafts,
    task_problem,
)
from app.research.crafts import QUESTION_MAX_CHARS
from app.research.knowledge_api import ComponentSummary
from app.research.open_work_texts import counted

from .component_library import library_components
from .knowledge_api import known_craft
from .open_work_components import registered_pieces
from .task_reservations import complete_task

__all__ = ["propose_component"]

APPROVED = "APPROVED"
PENDING = "PENDING"
OPEN_CONCEPT = "OPEN"
PLACE_KEY = re.compile(PLACE_KEY_PATTERN)
WAITING = "A proposal for {label} already waits for review or building."
NOT_IN_LIBRARY = "{labels} {verb} not in the component library; list_components gives the labels."
REFUSED = "{count} in the library already {verb} this; nothing was stored. Take one of the two ways on."
STORED = {
    PENDING: "Stored for review: an Admin approves or rejects it. Who proposed it is kept privately, never shown.",
    APPROVED: "Approved at once as a reviewer's own proposal; it waits to be built and registered.",
}


async def propose_component(
    session: AsyncSession, user: User, draft: ComponentProposalDraft, *, now: datetime
) -> ComponentProposalResult:
    problem = task_problem(draft)
    if problem is not None:
        raise InvalidInput(problem)
    await _check_labels(session, draft)
    owner = None if draft.craft_slug is None else await known_craft(session, draft.craft_slug)
    await _check_subjects(session, draft)
    matches = close_matches(draft, await _candidates(session, draft))
    if matches:
        verb = "shows" if len(matches) == 1 else "show"
        return ComponentProposalResult(
            outcome="REFUSED",
            label=draft.label,
            message=REFUSED.format(count=counted(len(matches), "component"), verb=verb),
            matches=matches,
            ways_on=list(WAYS_ON),
        )
    row = _proposal(draft, user, None if owner is None else owner.id, now=now)
    try:
        async with session.begin_nested():
            session.add(row)
    except IntegrityError as taken:
        raise InvalidInput(WAITING.format(label=draft.label)) from taken
    if draft.task_key is not None:
        await complete_task(session, user.id, draft.task_key, now=now)
    return ComponentProposalResult(
        outcome="STORED", proposal_id=row.id, status=row.status, label=draft.label, message=STORED[row.status]
    )


async def _check_labels(session: AsyncSession, draft: ComponentProposalDraft) -> None:
    named = [*draft.considered_labels, *([draft.extends] if draft.extends else [])]
    known = set(
        await session.scalars(
            select(KnowledgePiece.label).where(KnowledgePiece.label.in_(named), *registered_pieces())
        )
    )
    missing = [label for label in named if label not in known]
    if missing:
        verb = "is" if len(missing) == 1 else "are"
        raise InvalidInput(NOT_IN_LIBRARY.format(labels=", ".join(missing), verb=verb))
    if draft.extension == SUBJECT_LINK:
        return
    waiting = await session.scalar(
        select(ComponentProposal.id).where(
            ComponentProposal.label == draft.label,
            ComponentProposal.status.in_(LIVE_PROPOSALS),
            ComponentProposal.extension.is_distinct_from(SUBJECT_LINK),
        )
    )
    if waiting is not None:
        raise InvalidInput(WAITING.format(label=draft.label))


async def _check_subjects(session: AsyncSession, draft: ComponentProposalDraft) -> None:
    for subject in draft.subjects:
        if subject.kind == "CRAFT":
            await known_craft(session, subject.key)
        elif subject.kind == "PLACE" and not PLACE_KEY.match(subject.key):
            raise InvalidInput(f"{subject.key} is not a place key such as lgd:<district code>.")
    await _check_ids(session, draft, "CONCEPT", Concept.id, Concept.sensitivity == OPEN_CONCEPT)
    await _check_ids(session, draft, "COMPOUND", Compound.id)


async def _check_ids(
    session: AsyncSession, draft: ComponentProposalDraft, kind: str, column: Any, *rules: ColumnElement[bool]
) -> None:
    keys = [subject.key for subject in draft.subjects if subject.kind == kind]
    wanted = {key: _uuid(key, kind) for key in keys}
    if not wanted:
        return
    found = set(await session.scalars(select(column).where(column.in_(list(wanted.values())), *rules)))
    missing = [key for key, value in wanted.items() if value not in found]
    if missing:
        raise InvalidInput(f"No {kind.lower()} has the id {', '.join(missing)}.")


def _uuid(key: str, kind: str) -> uuid.UUID:
    try:
        return uuid.UUID(key)
    except ValueError as wrong:
        raise InvalidInput(f"A {kind.lower()} subject is named by its id; {key} is not one.") from wrong


async def _candidates(session: AsyncSession, draft: ComponentProposalDraft) -> list[ComponentSummary]:
    words = f"{draft.title} {draft.description}"[:QUESTION_MAX_CHARS]
    found = [
        *await _same_label(session, draft.label),
        *(await library_components(session, query=words)).components,
    ]
    for slug in proposal_crafts(draft):
        found += (await library_components(session, slug=slug, kind=draft.kind)).components
    return found


async def _same_label(session: AsyncSession, label: str) -> Sequence[ComponentSummary]:
    row = (
        await session.execute(
            select(KnowledgePiece, Craft.slug)
            .outerjoin(Craft, Craft.id == KnowledgePiece.craftId)
            .where(KnowledgePiece.label == label, *registered_pieces())
        )
    ).first()
    if row is None:
        return []
    piece, owner = row
    return [
        ComponentSummary(
            label=piece.label,
            title=piece.title,
            description=piece.description,
            kind=piece.kind,
            field=piece.facet,
            fields=piece.fields,
            craft_slug=owner,
            subjects=[],
        )
    ]


def _proposal(
    draft: ComponentProposalDraft, user: User, craft_id: uuid.UUID | None, *, now: datetime
) -> ComponentProposal:
    approved = has_rank(user, PROFESSOR)
    return ComponentProposal(
        proposerId=user.id,
        label=draft.label,
        title=draft.title,
        description=draft.description,
        kind=draft.kind,
        field=draft.field,
        fields=list(draft.fields),
        craftId=craft_id,
        subjects=[subject.model_dump(mode="json") for subject in draft.subjects],
        consideredLabels=list(draft.considered_labels),
        extendsLabel=draft.extends,
        extension=draft.extension,
        taskKey=draft.task_key,
        status=APPROVED if approved else PENDING,
        reviewedById=user.id if approved else None,
        reviewedAt=now if approved else None,
    )
