from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Literal

from pydantic import Field, PrivateAttr

from app.core.errors import InvalidInput, Refused
from app.core.mcp_scopes import CONTRIBUTE_SCOPE
from app.core.rate_limit import PICTURE_CHECKS, PICTURE_CHECKS_PER_WINDOW
from app.models import User
from app.models.media_refs import CHECK_REASON_MAX_CHARS, CHECK_REASON_MIN_CHARS
from app.research.picture_checks import (
    BATCH_DEFAULT,
    BATCH_MAX,
    SHOWS,
    VERDICT_WORDS,
    VERDICTS_PER_CALL_MAX,
    PictureChecks,
    RecordedCheck,
)
from app.research.review_switch import AGENT
from app.services.page_revalidation import claim_owners, refresh_pages
from app.services.picture_check_batches import CheckBatch, check_source, take_batch
from app.services.picture_check_records import GivenVerdict, Recorded, record_verdict
from app.services.task_reservations import holding
from app.services.trust_tiers import account_standing, publishes_at_once

from .mcp_protocol import ToolImage
from .mcp_tool_base import OPEN_WRITES, PICTURES, Arguments, Tool, ToolContext, contributor
from .proposal_limits import spent_limit

__all__ = ["CHECK_PICTURES", "CHECK_TOOLS", "ChecksReply"]

CHECKS_DO = "check pictures"
CHECK_DESCRIPTION = (
    "Hands out and records checks of the searched pictures the site shows beside facts, chosen by their words "
    "alone: whether each shows what its fact says, in this craft, and not a product, a stock photograph or "
    "another craft. take reserves a batch for this account, the most-served pictures ahead of the rest, each "
    "picture given as an image with its fact, title, caption and credit. verdicts records shows or "
    "does_not_show for each link_id, with a reason of 12 to 300 characters saying what the picture shows; they "
    "are recorded before the next batch is taken. A refusal hides that picture beside that fact at once; a "
    "picture is marked seen when a "
    "trusted account or two accounts agree, and disagreement goes to an Admin. One look per account per "
    f"link, {PICTURE_CHECKS_PER_WINDOW} an hour."
)
NOTHING_LEFT = "No searched picture waits for this account's look right now."
FULL = "This account holds as many tasks as its trust tier allows; record verdicts or give some back first."
TAKEN = (
    "Look at each picture and record shows or does_not_show for its link_id with what the picture shows. "
    "The batch is held for two hours."
)
SKIPPED = " {skipped} pictures could not be fetched and were left out."


class CheckedVerdict(Arguments):
    link_id: uuid.UUID = Field(description="A picture's link_id, as its batch gave it")
    verdict: Literal[*VERDICT_WORDS] = Field(description="shows or does_not_show")
    reason: str = Field(
        min_length=CHECK_REASON_MIN_CHARS,
        max_length=CHECK_REASON_MAX_CHARS,
        description="What the picture shows, in the checker's own words",
    )


class CheckPictures(Arguments):
    verdicts: list[CheckedVerdict] = Field(
        default_factory=list,
        max_length=VERDICTS_PER_CALL_MAX,
        description="Verdicts to record before any batch is taken",
    )
    take: int = Field(
        default=BATCH_DEFAULT, ge=0, le=BATCH_MAX, description="Pictures to take next; 0 takes none"
    )


class ChecksReply(PictureChecks):
    _images: list[ToolImage] = PrivateAttr(default_factory=list)

    def showing(self, images: list[ToolImage]) -> ChecksReply:
        self._images = list(images)
        return self

    def tool_images(self) -> list[ToolImage]:
        return list(self._images)


async def _check_pictures(context: ToolContext, arguments: CheckPictures) -> ChecksReply:
    user, now = contributor(context, "check_pictures", CHECKS_DO), datetime.now(UTC)
    recorded = await _recorded(context, user, arguments.verdicts, now=now)
    await _refreshed(context, recorded)
    batch = None
    if arguments.take:
        async with check_source() as source:
            batch = await take_batch(context.session, user, take=arguments.take, source=source, now=now)
    standing = await account_standing(context.session, user.id)
    reply = ChecksReply(
        recorded=[each.check if isinstance(each, Recorded) else each for each in recorded],
        pictures=[] if batch is None else [shown.item for shown in batch.shown],
        skipped=0 if batch is None else batch.skipped,
        holding=await holding(context.session, user.id, now=now),
        holding_max=standing.tasks_held_max,
        message=_message(batch),
    )
    return reply.showing(_images(batch))


async def _recorded(
    context: ToolContext, user: User, verdicts: list[CheckedVerdict], *, now: datetime
) -> list[Recorded | RecordedCheck]:
    trusted = await publishes_at_once(context.session, user.id, AGENT)
    recorded: list[Recorded | RecordedCheck] = []
    for each in {verdict.link_id: verdict for verdict in verdicts}.values():
        spent = await spent_limit(PICTURE_CHECKS, user)
        if spent is not None:
            recorded.append(RecordedCheck(link_id=each.link_id, refused=spent.message))
            continue
        given = GivenVerdict(each.link_id, VERDICT_WORDS[each.verdict] == SHOWS, each.reason)
        try:
            async with context.session.begin_nested():
                recorded.append(await record_verdict(context.session, user, given, trusted=trusted, now=now))
        except (InvalidInput, Refused) as refused:
            recorded.append(RecordedCheck(link_id=each.link_id, refused=str(refused)))
    return recorded


async def _refreshed(context: ToolContext, recorded: list[Recorded | RecordedCheck]) -> None:
    changed = [
        each.claim_id
        for each in recorded
        if isinstance(each, Recorded) and (each.state.refused or each.state.vision)
    ]
    if not changed:
        return
    await context.session.commit()
    await refresh_pages(await claim_owners(context.session, changed))


def _message(batch: CheckBatch | None) -> str:
    if batch is None:
        return "Recorded. Call again with take to look at more."
    said = SKIPPED.format(skipped=batch.skipped) if batch.skipped else ""
    if batch.shown:
        return TAKEN + said
    return (FULL if batch.full else NOTHING_LEFT) + said


def _images(batch: CheckBatch | None) -> list[ToolImage]:
    if batch is None:
        return []
    return [
        ToolImage(
            caption=f"Picture {shown.item.position} (link_id {shown.item.link_id}): {shown.item.title}",
            data=shown.picture.data,
            mime="image/jpeg",
        )
        for shown in batch.shown
    ]


CHECK_PICTURES = Tool(
    "check_pictures",
    "Check searched pictures",
    CHECK_DESCRIPTION,
    CheckPictures,
    ChecksReply,
    _check_pictures,
    CONTRIBUTE_SCOPE,
    OPEN_WRITES,
    group=PICTURES,
)
CHECK_TOOLS: tuple[Tool, ...] = (CHECK_PICTURES,)
