from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.errors import InvalidInput
from app.core.roles import ADMIN, has_rank
from app.models import ArticleSection, Craft, CraftCategory, SectionProposal, User
from app.research.category_page import category_path
from app.research.contribution_queue import FollowedProposal
from app.research.knowledge_writes import ProposalSubject
from app.research.section_proposals import (
    APPROVED_STATUS,
    PENDING_STATUS,
    REFUSED,
    REJECTED_STATUS,
    PublishedSection,
    SectionCheck,
    SectionTicket,
    first_refusal,
)

from .contribution_queue_tickets import NOT_YOURS, own_ticket
from .section_proposals import MESSAGES

__all__ = ["followed_proposal", "section_ticket"]

CRAFT = "craft"
CATEGORY = "category"
CRAFT_PATH = "/crafts/"
PUBLISHED = "PUBLISHED"
WAITING_WORDS = (
    "Waiting for review: a Professor or Admin reads it beside the field's published section, and approval "
    "puts it in that section's place."
)
SHOWN_WORDS = (
    "Approved: it is the page's {field} section now, version {version}, shown after the page's next refresh."
)
LATER_WORDS = (
    "Approved and published as version {version}; it is no longer the page's {field} section ({status})."
)
GONE_WORDS = "Approved, and the section it became is no longer held."
REJECTED_WORDS = "Rejected by its reviewer: {note}"


async def followed_proposal(session: AsyncSession, user: User, proposal_id: uuid.UUID) -> FollowedProposal:
    row = await session.get(SectionProposal, proposal_id)
    if row is None:
        return FollowedProposal(await own_ticket(session, user, proposal_id))
    if row.proposerId != user.id and not has_rank(user, ADMIN):
        raise InvalidInput(NOT_YOURS.format(proposal_id=proposal_id))
    return FollowedProposal(await section_ticket(session, row))


async def section_ticket(session: AsyncSession, row: SectionProposal) -> SectionTicket:
    subject = await _subject(session, row)
    checks = [SectionCheck.model_validate(check) for check in row.checks]
    section = await _became(session, row, subject)
    return SectionTicket(
        proposal_id=row.id,
        status=row.status,
        subject=subject,
        field=row.field,
        sentences=row.sentences,
        checks=checks,
        task_key=row.taskKey,
        note=row.note,
        proposed_at=row.createdAt,
        reviewed_at=row.reviewedAt,
        review_note=row.reviewNote,
        section=section,
        message=_said(row, checks, section),
    )


async def _subject(session: AsyncSession, row: SectionProposal) -> ProposalSubject:
    if row.categoryId is not None:
        slug = await session.scalar(select(CraftCategory.slug).where(CraftCategory.id == row.categoryId))
        return ProposalSubject(kind=CATEGORY, slug=str(slug))
    slug = await session.scalar(select(Craft.slug).where(Craft.id == row.craftId))
    return ProposalSubject(kind=CRAFT, slug=str(slug))


async def _became(
    session: AsyncSession, row: SectionProposal, subject: ProposalSubject
) -> PublishedSection | None:
    if row.status != APPROVED_STATUS or row.sectionId is None:
        return None
    section = await session.get(ArticleSection, row.sectionId)
    if section is None:
        return None
    path = category_path(subject.slug) if subject.kind == CATEGORY else f"{CRAFT_PATH}{subject.slug}"
    page_url = f"{get_settings().public_web_url.rstrip('/')}{path}"
    return PublishedSection(version=section.version, status=section.status, page_url=page_url)


def _said(row: SectionProposal, checks: list[SectionCheck], section: PublishedSection | None) -> str:
    refused = first_refusal(checks)
    if refused is not None:
        return MESSAGES[REFUSED].format(check=refused.check, reason="; ".join(refused.reasons))
    if row.status == PENDING_STATUS:
        return WAITING_WORDS
    if row.status == REJECTED_STATUS:
        return REJECTED_WORDS.format(note=row.reviewNote or "no reason was kept")
    if section is None:
        return GONE_WORDS
    words = SHOWN_WORDS if section.status == PUBLISHED else LATER_WORDS
    return words.format(field=row.field, version=section.version, status=section.status)
