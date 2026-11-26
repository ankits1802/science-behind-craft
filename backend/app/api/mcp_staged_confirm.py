from __future__ import annotations

import uuid
from collections.abc import Mapping
from datetime import UTC, datetime
from types import MappingProxyType
from typing import Any

from pydantic import BaseModel, Field

from app.core.errors import InvalidInput
from app.core.mcp_scopes import REVIEW_SCOPE
from app.core.roles import Capability, can
from app.models import User
from app.research.base import ContractModel, absent
from app.research.staged_reviews import (
    APPLIED,
    BATCH_DAYS,
    REFUSED,
    STAGED_ITEMS_PER_DAY_MAX,
    StagedBatchView,
)
from app.services.review_queue_errors import DecisionConflict, NotYourQueue, UnknownItem
from app.services.staged_review_confirm import confirm_as_staged
from app.services.staged_review_finish import finish_confirmed
from app.services.staged_review_summary import StagedSummary, own_open_batch, staged_summary
from app.services.staged_review_views import batch_view

from .mcp_input import Answer, Question, choice, yes_no
from .mcp_tool_base import AsksAfter, FollowUp, ToolContext

__all__ = [
    "CONFIRM_IN_CLIENT",
    "CONFIRM_KEY",
    "REVIEW_PAGE",
    "StageReply",
    "StagedLine",
    "chosen_positions",
    "confirm_question",
]

REVIEW_PAGE = "/admin/review"
CONFIRM_KEY = "confirm"
CHOICE = "choice"
ALL, SOME, NONE = "all", "some", "none"
BATCH_REF, STAGED_REF = "batch", "staged"
TICK = "item_{number}"
CONFIRM_MESSAGE = (
    "Your AI client {client} staged {count} review decisions for you. Nothing is published or changed until a "
    "person confirms; only your answer here counts, and each decision you confirm runs the Review page's own "
    "checks again. What you leave waits on {url} for {days} days.\n\n{lines}"
)
CHOICES = (
    (ALL, "Confirm all of them"),
    (SOME, "Confirm only the ones I tick below"),
    (NONE, "Confirm none now; they wait on the Review page"),
)
CHOICE_HELP = "All, only the ticked ones, or none for now"
TICK_HELP = "Counts only when you choose to confirm the ones you tick"
WAITS = (
    "The person {how} in their client, so nothing is published yet: the staged batch waits until an Admin "
    "confirms it on {url}, within {days} days."
)
DECLINED, NONE_CHOSEN, NONE_TICKED, UNANSWERED = (
    "declined to confirm",
    "chose to confirm none of it",
    "ticked none of it",
    "gave no answer",
)
CONFIRMED_HERE = (
    "The person confirmed {chosen} of {count} staged decisions in their client: {applied} applied, {refused} "
    "refused by the checks, the rest left out of the batch. {refresh}"
)
GONE = "The staged batch is no longer open to this account, so nothing was confirmed; see {url}."
NO_BACKGROUND = "This server cannot refresh pages from here, so nothing was confirmed; confirm on {url}."
NOT_CONFIRMED = "The person's confirmation was refused, so nothing was confirmed: {reason}"
NOT_A_REVIEWER = "stage_reviews is for Admin and Master Admin accounts signed in with the review scope."


class StagedLine(ContractModel):
    index: int
    kind: str
    id: uuid.UUID | None = None
    action: str | None = None
    label: str | None = None
    reason: str | None = None


class StageReply(ContractModel):
    batch_id: uuid.UUID | None
    staged: list[StagedLine]
    refused: list[StagedLine]
    staged_today: int
    per_day_max: int = STAGED_ITEMS_PER_DAY_MAX
    expires_at: datetime | None
    confirm_at: str
    published: bool = False
    batch: StagedBatchView | None = Field(default=None, exclude_if=absent)
    message: str


def confirm_question(summary: StagedSummary, *, url: str) -> Question:
    lines = "\n".join(f"{line.position + 1}. {line.words}" for line in summary.lines)
    message = CONFIRM_MESSAGE.format(
        client=summary.client_name, count=len(summary.lines), url=url, days=BATCH_DAYS, lines=lines
    )
    properties: dict[str, Mapping[str, Any]] = {CHOICE: choice("Confirm", CHOICE_HELP, CHOICES)}
    for line in summary.lines:
        title = f"{line.position + 1}. {line.label}"
        properties[TICK.format(number=line.position + 1)] = yes_no(title, TICK_HELP, default=False)
    return Question(CONFIRM_KEY, message, MappingProxyType(properties), (CHOICE,))


def chosen_positions(answer: Answer | None, count: int) -> frozenset[int]:
    picked = None if answer is None else answer.text(CHOICE)
    if answer is None or picked not in (ALL, SOME):
        return frozenset()
    if picked == ALL:
        return frozenset(range(count))
    return frozenset(place for place in range(count) if answer.says_yes(TICK.format(number=place + 1)))


async def _ask(context: ToolContext, reply: BaseModel) -> FollowUp | None:
    person = _reviewer(context)
    if person is None or not isinstance(reply, StageReply) or reply.batch_id is None:
        return None
    now = datetime.now(UTC)
    batch = await own_open_batch(context.session, reply.batch_id, person, grant_id=_grant(context), now=now)
    if batch is None:
        return None
    summary = await staged_summary(context.session, batch, site=context.site)
    refs = {BATCH_REF: str(batch.id), STAGED_REF: reply.model_dump_json(by_alias=True)}
    return FollowUp(confirm_question(summary, url=_review_url(context)), MappingProxyType(refs))


async def _answered(context: ToolContext, arguments: Any, refs: Mapping[str, str]) -> StageReply:
    person = _reviewer(context)
    if person is None:
        raise InvalidInput(NOT_A_REVIEWER)
    staged = StageReply.model_validate_json(refs[STAGED_REF])
    answer = context.answers.get(CONFIRM_KEY)
    positions = chosen_positions(answer, len(staged.staged))
    if not positions:
        return staged.model_copy(update={"message": _waiting(answer, _review_url(context))})
    return await _confirmed(context, person, staged, uuid.UUID(refs[BATCH_REF]), positions)


async def _confirmed(
    context: ToolContext, person: User, staged: StageReply, batch_id: uuid.UUID, positions: frozenset[int]
) -> StageReply:
    url, now, session = _review_url(context), datetime.now(UTC), context.session
    batch = await own_open_batch(session, batch_id, person, grant_id=_grant(context), now=now)
    if batch is None:
        raise InvalidInput(GONE.format(url=url))
    if context.background is None:
        raise InvalidInput(NO_BACKGROUND.format(url=url))
    try:
        confirmed = await confirm_as_staged(session, batch.id, positions, person, now=now)
    except (UnknownItem, NotYourQueue, DecisionConflict) as refused:
        raise InvalidInput(NOT_CONFIRMED.format(reason=refused)) from None
    await session.commit()
    note = await finish_confirmed(session, confirmed, person, context.background, now=now)
    view = await batch_view(session, confirmed.batch, now=now, refresh=note)
    states = [item.state for item in view.items]
    said = CONFIRMED_HERE.format(
        chosen=len(positions),
        count=len(states),
        applied=states.count(APPLIED),
        refused=states.count(REFUSED),
        refresh=note or "",
    )
    return staged.model_copy(update={"batch": view, "published": APPLIED in states, "message": said.strip()})


def _waiting(answer: Answer | None, url: str) -> str:
    if answer is None:
        how = UNANSWERED
    elif not answer.accepted:
        how = DECLINED
    else:
        how = NONE_TICKED if answer.text(CHOICE) == SOME else NONE_CHOSEN
    return WAITS.format(how=how, url=url, days=BATCH_DAYS)


def _reviewer(context: ToolContext) -> User | None:
    user = context.user
    if user is None or REVIEW_SCOPE not in context.scopes or not can(user, Capability.REVIEW_CONTRIBUTIONS):
        return None
    return user


def _grant(context: ToolContext) -> uuid.UUID | None:
    return None if context.caller is None else context.caller.grant_id


def _review_url(context: ToolContext) -> str:
    return f"{context.site}{REVIEW_PAGE}"


CONFIRM_IN_CLIENT = AsksAfter(ask=_ask, answered=_answered)
