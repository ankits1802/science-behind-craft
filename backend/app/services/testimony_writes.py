from __future__ import annotations

import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import InvalidInput
from app.models import ArtisanContribution, ArtisanConversation, Claim, Craft, ReviewEvent
from app.research.testimony import (
    CORROBORATING_CLAIMS_MAX,
    REVIEW_NOTE_MAX,
    TESTIMONY_REJECT_REASONS,
    Draft,
    contribution_problems,
    move_allowed,
    quote_span,
)
from app.retrieval.statements import claim_conditions

from . import audit
from .conversation_retention import settle_retention
from .knowledge_view import craft_scope_of
from .reader_profiles import held_back_name_terms
from .testimony_claims import ClaimWrite, ensure_source, rewrite_credit, testimony_concept, write_claim
from .testimony_screens import contribution_screens, rescreen_contributions
from .testimony_store import (
    ContributionProblems,
    MoveRefused,
    StaleContribution,
    contribution_for_update,
    refuse_own,
)
from .testimony_withdrawal import (
    WithdrawnEverything,
    clear_expired_rejections,
    delete_conversation,
    erase_artisan,
    withdraw,
    withdraw_everything,
)

__all__ = [
    "ContributionEdit",
    "WithdrawnEverything",
    "approve",
    "clear_expired_rejections",
    "delete_conversation",
    "edit",
    "erase_artisan",
    "reject",
    "rescreen_contributions",
    "rewrite_credit",
    "withdraw",
    "withdraw_everything",
]

ENGLISH = "en"
REVIEWED = "REVIEWED"
ORIGINAL = "ORIGINAL"
EDITABLE = ("PENDING", "APPROVED")


@dataclass(frozen=True, kw_only=True)
class ContributionEdit:
    version: int
    quote: str | None = None
    english: str | None = None
    english_checked: bool = False
    claim_text: str | None = None
    discipline: str | None = None
    concept_type: str | None = None
    concept_name: str | None = None

    def fields(self) -> list[str]:
        names = {
            "quote": self.quote,
            "english": self.english,
            "claimText": self.claim_text,
            "discipline": self.discipline,
            "conceptType": self.concept_type,
            "conceptName": self.concept_name,
        }
        changed = [name for name, value in names.items() if value is not None]
        return [*changed, "englishSource"] if self.english_checked or self.english is not None else changed


def _checked(contribution: ArtisanContribution, version: int, target: str) -> None:
    if contribution.version != version:
        raise StaleContribution(f"contribution {contribution.id} is at version {contribution.version}")
    if not move_allowed(contribution.status, target):
        raise MoveRefused(f"a {contribution.status.lower()} contribution cannot become {target.lower()}")


def _approvable(contribution: ArtisanContribution) -> list[str]:
    problems: list[str] = []
    if contribution.screens:
        problems.append("a held-back name is in the quote, the English or the claim; edit it out first")
    if contribution.english is None and contribution.quoteLanguage != ENGLISH:
        problems.append("a quote not in English needs its English")
    if not contribution.quote or not contribution.claimText:
        problems.append("the quote and the claim are needed")
    return problems


async def _corroborating(
    session: AsyncSession, craft_id: uuid.UUID, claim_ids: Sequence[uuid.UUID]
) -> list[uuid.UUID]:
    wanted = list(dict.fromkeys(claim_ids))
    if len(wanted) > CORROBORATING_CLAIMS_MAX:
        raise ContributionProblems([f"at most {CORROBORATING_CLAIMS_MAX} corroborating claims"])
    if not wanted:
        return []
    craft = await session.get(Craft, craft_id)
    if craft is None:
        raise ContributionProblems(["the contribution's craft is gone"])
    conditions = claim_conditions(craft_scope_of(craft), mode="HYBRID")
    found = set(await session.scalars(select(Claim.id).where(Claim.id.in_(wanted), *conditions)))
    missing = [str(claim_id) for claim_id in wanted if claim_id not in found]
    if missing:
        raise ContributionProblems(
            [f"claim {claim_id} is not a visible claim of this craft" for claim_id in missing]
        )
    return wanted


async def _record(
    session: AsyncSession,
    reviewer: Any,
    contribution: ArtisanContribution,
    action: str,
    detail: dict[str, Any],
) -> None:
    await audit.record(
        session,
        action=action,
        actor=reviewer,
        target_type="ArtisanContribution",
        target_id=contribution.id,
        detail=detail,
    )


def _reviewed(contribution: ArtisanContribution, reviewer: Any, now: datetime) -> None:
    contribution.reviewedById = reviewer.id
    contribution.reviewedAt = now
    contribution.version += 1


async def _publish(
    session: AsyncSession, contribution: ArtisanContribution, reviewer: Any, *, now: datetime
) -> Claim:
    conversation = await session.get(ArtisanConversation, contribution.conversationId, with_for_update=True)
    craft = await session.get(Craft, contribution.craftId)
    if conversation is None or craft is None:
        raise ContributionProblems(["the contribution's conversation or craft is gone"])
    source = await ensure_source(session, conversation, craft)
    concept = await testimony_concept(session, craft.id, contribution.conceptType, contribution.conceptName)
    write = ClaimWrite(
        contribution=contribution,
        concept_id=concept.id,
        source_id=source.id,
        reviewer_id=reviewer.id,
        now=now,
        supersedes=contribution.claimId,
    )
    return await write_claim(session, write)


async def approve(
    session: AsyncSession,
    contribution_id: uuid.UUID,
    reviewer: Any,
    *,
    version: int,
    english_checked: bool,
    corroborating_ids: Sequence[uuid.UUID],
    now: datetime,
) -> ArtisanContribution:
    contribution = await contribution_for_update(session, contribution_id)
    refuse_own(contribution, reviewer)
    _checked(contribution, version, "APPROVED")
    if english_checked and contribution.englishSource != ORIGINAL:
        contribution.englishSource = REVIEWED
    terms = await held_back_name_terms(session, contribution.userId)
    contribution.screens = contribution_screens(contribution, terms)
    problems = _approvable(contribution)
    if problems:
        raise ContributionProblems(problems)
    contribution.corroboratingClaimIds = await _corroborating(
        session, contribution.craftId, corroborating_ids
    )
    source_status = contribution.status
    if source_status == "PENDING":
        await _first_approval(session, contribution, reviewer, now=now)
    _reviewed(contribution, reviewer, now)
    await session.flush()
    await settle_retention(session, contribution.conversationId, now=now, at_once=False)
    fields = ["corroboratingClaimIds", *(["englishSource"] if english_checked else [])]
    await _record(
        session,
        reviewer,
        contribution,
        "testimony.approved",
        {"from": source_status, "to": "APPROVED", "fields": fields},
    )
    return contribution


async def _first_approval(
    session: AsyncSession, contribution: ArtisanContribution, reviewer: Any, *, now: datetime
) -> None:
    claim = await _publish(session, contribution, reviewer, now=now)
    contribution.status = "APPROVED"
    contribution.claimId = claim.id
    contribution.approvedAt = now


def _edited_quote(contribution: ArtisanContribution, quote: str, turn_text: str) -> str:
    old = quote_span(contribution.quote or "", turn_text) if contribution.quote else None
    span = quote_span(quote, turn_text, near=old[0] if old else None)
    if span is None:
        raise ContributionProblems(
            ["the quote is a span of the artisan's own words in this turn, on whole words"]
        )
    return turn_text[span[0] : span[1]]


def _apply(contribution: ArtisanContribution, change: ContributionEdit, turn_text: str) -> None:
    if change.quote is not None:
        contribution.quote = _edited_quote(contribution, change.quote, turn_text)
    if change.english is not None:
        contribution.english = change.english.strip()
    if change.claim_text is not None:
        contribution.claimText = change.claim_text.strip()
    if change.discipline is not None:
        contribution.discipline = change.discipline
    if change.concept_type is not None:
        contribution.conceptType = change.concept_type
    if change.concept_name is not None:
        contribution.conceptName = " ".join(change.concept_name.split())
    if change.english is not None or (change.english_checked and contribution.englishSource != ORIGINAL):
        contribution.englishSource = REVIEWED


def _draft(contribution: ArtisanContribution) -> Draft:
    return Draft(
        quote=contribution.quote or "",
        english=contribution.english or "",
        claim=contribution.claimText or "",
        discipline=contribution.discipline,
        concept_type=contribution.conceptType,
        concept_name=contribution.conceptName,
    )


async def edit(
    session: AsyncSession,
    contribution_id: uuid.UUID,
    reviewer: Any,
    *,
    change: ContributionEdit,
    turn_text: str,
    now: datetime,
) -> ArtisanContribution:
    contribution = await contribution_for_update(session, contribution_id)
    refuse_own(contribution, reviewer)
    if contribution.version != change.version:
        raise StaleContribution(f"contribution {contribution.id} is at version {contribution.version}")
    if contribution.status not in EDITABLE:
        raise MoveRefused(f"a {contribution.status.lower()} contribution cannot be edited")
    _apply(contribution, change, turn_text)
    problems = contribution_problems(_draft(contribution), turn_text)
    if problems:
        raise ContributionProblems(problems)
    contribution.screens = contribution_screens(
        contribution, await held_back_name_terms(session, contribution.userId)
    )
    if contribution.status == "APPROVED":
        problems = _approvable(contribution)
        if problems:
            raise ContributionProblems(problems)
        await _supersede(session, contribution, reviewer, now=now)
    _reviewed(contribution, reviewer, now)
    await _record(session, reviewer, contribution, "testimony.edited", {"fields": change.fields()})
    return contribution


async def _supersede(
    session: AsyncSession, contribution: ArtisanContribution, reviewer: Any, *, now: datetime
) -> None:
    old = (
        await session.get(Claim, contribution.claimId, with_for_update=True) if contribution.claimId else None
    )
    claim = await _publish(session, contribution, reviewer, now=now)
    if old is not None:
        old.status = "SUPERSEDED"
        session.add(
            ReviewEvent(
                claimId=old.id,
                actorId=reviewer.id,
                actorKind="USER",
                fromStatus="APPROVED",
                toStatus="SUPERSEDED",
            )
        )
    contribution.claimId = claim.id


def _reason_problems(reason: str, note: str | None) -> list[str]:
    problems: list[str] = []
    if reason not in TESTIMONY_REJECT_REASONS:
        problems.append(f"the reason is one of {', '.join(TESTIMONY_REJECT_REASONS)}")
    if reason == "OTHER" and not (note or "").strip():
        problems.append("a reason of OTHER needs a note")
    if note is not None and len(note) > REVIEW_NOTE_MAX:
        problems.append(f"a note is at most {REVIEW_NOTE_MAX} characters")
    return problems


async def reject(
    session: AsyncSession,
    contribution_id: uuid.UUID,
    reviewer: Any,
    *,
    version: int,
    reason: str,
    note: str | None,
    now: datetime,
) -> ArtisanContribution:
    problems = _reason_problems(reason, note)
    if problems:
        raise InvalidInput("; ".join(problems))
    contribution = await contribution_for_update(session, contribution_id)
    refuse_own(contribution, reviewer)
    _checked(contribution, version, "REJECTED")
    source_status = contribution.status
    if source_status == "APPROVED" and contribution.claimId is not None:
        await _retract(session, contribution.claimId, reviewer)
    contribution.status = "REJECTED"
    contribution.rejectReason = reason
    contribution.reviewNote = (note or "").strip() or None
    contribution.rejectedAt = now
    _reviewed(contribution, reviewer, now)
    await session.flush()
    await settle_retention(session, contribution.conversationId, now=now, at_once=False)
    detail = {"from": source_status, "to": "REJECTED", "fields": ["rejectReason", "reviewNote"]}
    await _record(session, reviewer, contribution, "testimony.rejected", detail)
    return contribution


async def _retract(session: AsyncSession, claim_id: uuid.UUID, reviewer: Any) -> None:
    claim = await session.get(Claim, claim_id, with_for_update=True)
    if claim is None:
        return
    claim.status = "RETRACTED"
    session.add(
        ReviewEvent(
            claimId=claim.id,
            actorId=reviewer.id,
            actorKind="USER",
            fromStatus="APPROVED",
            toStatus="RETRACTED",
        )
    )
