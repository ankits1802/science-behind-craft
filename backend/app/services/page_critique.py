from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import LayoutProposal, PagePreview, User
from app.research.design_critique import DesignCritique
from app.research.page_proposals import ACCEPTED, LAYOUT, PagePreviewResult, PageProposalResult

from .page_preview_links import preview_key, preview_token, token_preview
from .page_reviews import DrawnPreview

__all__ = [
    "attach_critique",
    "carry_critique",
    "critiqued",
    "latest_critique",
    "layout_critique",
    "stored_critique",
]


async def critiqued(
    session: AsyncSession,
    user: User,
    previewed: PagePreviewResult,
    drawn: DrawnPreview,
    *,
    critique: DesignCritique | None,
    now: datetime,
) -> DrawnPreview:
    if critique is None:
        return drawn
    preview_id = token_preview(preview_token(previewed.preview_url), user.id, preview_key(), now=now)
    row = await session.get(PagePreview, preview_id)
    if row is not None:
        row.critique = critique.model_dump(mode="json")
        await session.flush()
    if drawn.report is None:
        return drawn
    return DrawnPreview(report=drawn.report.model_copy(update={"critique": critique}), images=drawn.images)


async def latest_critique(
    session: AsyncSession, user_id: uuid.UUID, subject: tuple[str, str], *, now: datetime
) -> DesignCritique | None:
    kind, slug = subject
    stored = await session.scalar(
        select(PagePreview.critique)
        .where(
            PagePreview.userId == user_id,
            PagePreview.subjectKind == kind,
            PagePreview.subjectSlug == slug,
            PagePreview.critique.is_not(None),
            PagePreview.expiresAt > now,
        )
        .order_by(PagePreview.createdAt.desc())
        .limit(1)
    )
    return stored_critique(stored)


async def attach_critique(
    session: AsyncSession, user: User, result: PageProposalResult, *, now: datetime
) -> None:
    if _accepted_layout(result) is None:
        return
    subject = (result.subject.kind, result.subject.slug)
    await carry_critique(session, result, await latest_critique(session, user.id, subject, now=now))


async def carry_critique(
    session: AsyncSession, result: PageProposalResult, critique: DesignCritique | None
) -> None:
    layout = _accepted_layout(result)
    proposal = None if critique is None or layout is None else await session.get(LayoutProposal, layout)
    if critique is None or proposal is None:
        return
    proposal.critique = critique.model_dump(mode="json")
    await session.flush()


def layout_critique(proposal: LayoutProposal) -> DesignCritique | None:
    return stored_critique(proposal.critique)


def stored_critique(stored: object) -> DesignCritique | None:
    if not isinstance(stored, dict):
        return None
    try:
        return DesignCritique.model_validate(stored)
    except ValidationError:
        return None


def _accepted_layout(result: PageProposalResult) -> uuid.UUID | None:
    part = next((part for part in result.parts if part.part == LAYOUT and part.outcome == ACCEPTED), None)
    return None if part is None or part.id is None else uuid.UUID(part.id)
