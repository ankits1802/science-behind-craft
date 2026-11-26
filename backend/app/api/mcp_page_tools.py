from __future__ import annotations

import base64
import uuid
from datetime import UTC, datetime

from pydantic import Field, PrivateAttr

from app.core.errors import InvalidInput
from app.core.mcp_scopes import CONTRIBUTE_SCOPE
from app.core.rate_limit import PAGE_PREVIEWS, PAGE_PROPOSALS
from app.data.page_preview_view import PAGE_PREVIEW_VIEW_URI
from app.models import PageDraft, User
from app.research.base import absent
from app.research.page_drafts import DraftView, PageLists, parts_counts
from app.research.page_proposals import PageBundle, PagePreviewResult, PageProposalResult
from app.research.page_render import RenderedImage
from app.research.page_report import PageReport
from app.research.review_switch import AGENT
from app.services import page_drafts, page_holds, page_preview, page_report, page_reviews
from app.services.borrowed_placements import held_refusal
from app.services.component_lifecycle import withdrawn_owners
from app.services.page_renders import page_renderer
from app.services.page_revalidation import refresh_pages
from app.services.trust_tiers import publishes_at_once

from .mcp_guide_steps import (
    HandedGuide,
    design_sheets,
    failed_rules_guide,
    handed,
    kinds_guide,
    refuse_unread,
)
from .mcp_page_arguments import ONE_PAGE, ONE_WORK, EditDraft, PageWork, PreviewWork, bundle_parts
from .mcp_page_texts import (
    ADD,
    CONFIRM,
    CREATED,
    EDIT_DESCRIPTION,
    FIX_FIRST,
    FOLLOW,
    HELD,
    PREVIEW,
    PREVIEW_DESCRIPTION,
    PROPOSE_DESCRIPTION,
    REVIEWED,
    SUBMITTED,
)
from .mcp_protocol import ToolImage
from .mcp_studio_arguments import STUDIO_DOES
from .mcp_tool_base import PAGES, READ_ONLY, WRITES, Tool, ToolContext, contributor
from .page_proposal_deps import page_proposed
from .proposal_limits import refuse_tool_when_spent

__all__ = ["PAGE_TOOLS", "PICTURE_MIME", "DraftReply", "PageReply", "PreviewReply"]

PICTURE_MIME = "image/jpeg"


class DraftReply(DraftView):
    notices: list[str] = Field(default_factory=list)
    guide: HandedGuide | None = Field(default=None, exclude_if=absent)


class PreviewReply(PagePreviewResult):
    draft_id: uuid.UUID | None = None
    report: PageReport | None = None
    next_step: str = REVIEWED
    notices: list[str] = Field(default_factory=list)
    guide: HandedGuide | None = Field(default=None, exclude_if=absent)
    _images: list[ToolImage] = PrivateAttr(default_factory=list)

    def showing(self, images: list[ToolImage]) -> PreviewReply:
        self._images = list(images)
        return self

    def tool_images(self) -> list[ToolImage]:
        return list(self._images)


class PageReply(PageProposalResult):
    draft_id: uuid.UUID | None = None
    next_step: str | None = None
    notices: list[str] = Field(default_factory=list)


def _held(row: PageDraft) -> str:
    counts = parts_counts(page_drafts.held_parts(row))
    return HELD.format(
        facts=counts.facts, structure=counts.structure, components=counts.components, pictures=counts.pictures
    )


async def _opened(
    context: ToolContext, user: User, arguments: EditDraft, now: datetime
) -> tuple[PageDraft, str]:
    if arguments.draft_id is not None:
        changing = arguments.changes()
        row = await page_drafts.own_draft(
            context.session, user, arguments.draft_id, now=now, open_only=changing
        )
        return row, ""
    if arguments.subject is None:
        raise InvalidInput(ONE_PAGE)
    row = await page_drafts.create_draft(context.session, user, arguments.subject, now=now)
    return row, CREATED.format(kind=row.subjectKind, slug=row.subjectSlug) + " "


async def _edit_draft(context: ToolContext, arguments: EditDraft) -> DraftReply:
    user, now = contributor(context, "edit_draft", STUDIO_DOES), datetime.now(UTC)
    row, opened = await _opened(context, user, arguments, now)
    kinds = arguments.component_kinds()
    if kinds and not page_drafts.held_parts(row).components:
        refuse_unread(arguments.read_token)
    for removed in arguments.removals():
        row = await page_drafts.remove_from_draft(context.session, user, row.id, removed, now=now)
    addition = arguments.addition()
    if addition is not None:
        row = await page_drafts.add_to_draft(context.session, user, row.id, addition, now=now)
    changed = arguments.changes()
    step = SUBMITTED if row.result else (PREVIEW if changed else ADD)
    view = page_drafts.draft_view(row, message=f"{opened}{_held(row)}", next_step=step, full=not changed)
    return DraftReply.model_validate(
        {
            **view.model_dump(),
            "notices": arguments.notices(),
            "guide": _draft_guide(row, kinds, opened=bool(opened)),
        }
    )


def _draft_guide(row: PageDraft, kinds: list[str], *, opened: bool) -> HandedGuide | None:
    if kinds or not opened or page_drafts.held_parts(row).components:
        return kinds_guide(kinds)
    return handed(design_sheets())


async def _work(
    context: ToolContext, user: User, arguments: PageWork, now: datetime
) -> tuple[PageBundle, PageDraft | None, PageLists | None]:
    if arguments.draft_id is None:
        if arguments.bundle is None:
            raise InvalidInput(ONE_WORK)
        return arguments.bundle, None, None
    row = await page_drafts.own_draft(context.session, user, arguments.draft_id, now=now, lock=True)
    return page_drafts.bundle_of(row), row, page_drafts.held_parts(row).lists


async def _preview_page(context: ToolContext, arguments: PreviewWork) -> PreviewReply:
    user, now = contributor(context, "preview_page", STUDIO_DOES), datetime.now(UTC)
    if arguments.builds_components():
        refuse_unread(arguments.read_token)
    bundle, row, lists = await _work(context, user, arguments, now)
    await refuse_tool_when_spent(PAGE_PREVIEWS, user)
    previewed = await page_preview.preview_page(context.session, user, bundle, site=context.site, now=now)
    report = await page_report.preview_report(context.session, user, bundle, previewed, lists=lists, now=now)
    drawn = await page_reviews.drawn_preview(
        context.session, user, previewed, report, renderer=page_renderer(), now=now
    )
    if row is not None:
        await page_drafts.record_preview(context.session, row, previewed, drawn.report)
    reply = PreviewReply.model_validate(
        {
            **previewed.model_dump(),
            "draftId": arguments.draft_id,
            "report": drawn.report,
            "notices": arguments.notices(),
            "guide": failed_rules_guide(drawn.report),
        }
    )
    return reply.showing(_pictures(drawn.images))


def _pictures(images: list[RenderedImage]) -> list[ToolImage]:
    return [
        ToolImage(caption=image.caption, data=base64.b64decode(image.data), mime=PICTURE_MIME)
        for image in images
    ]


async def _propose_page(context: ToolContext, arguments: PageWork) -> PageReply:
    user, now = contributor(context, "propose_page", STUDIO_DOES), datetime.now(UTC)
    bundle, row, _ = await _work(context, user, arguments, now)
    whole = row is not None or bundle_parts(bundle) > 1
    if whole:
        await refuse_tool_when_spent(PAGE_PROPOSALS, user)
    if whole and await publishes_at_once(context.session, user.id, AGENT):
        return await _hold_page(context, user, (bundle, row), arguments, now)
    result = await page_proposed(context.session, bundle, user, origin=AGENT, site=context.site)
    if row is not None:
        await page_drafts.record_submission(context.session, row, result, now=now)
    await _refresh_withdrawn(context, result)
    return _page_reply(result, arguments, FOLLOW if row is None else SUBMITTED)


async def _hold_page(
    context: ToolContext,
    user: User,
    work: tuple[PageBundle, PageDraft | None],
    arguments: PageWork,
    now: datetime,
) -> PageReply:
    bundle, row = work
    refused = await held_refusal(context.session, bundle, site=context.site)
    if refused is not None:
        return _page_reply(refused, arguments, FIX_FIRST)
    client = context.caller.client_name if context.caller is not None else None
    place = page_holds.HoldPlace(site=context.site, client_name=client, now=now)
    result = await page_holds.hold_page(context.session, user, bundle, row, place)
    return _page_reply(result, arguments, CONFIRM)


async def _refresh_withdrawn(context: ToolContext, result: PageProposalResult) -> None:
    owners = await withdrawn_owners(context.session, result.parts)
    if owners.empty:
        return
    await context.session.commit()
    await refresh_pages(owners)


def _page_reply(result: PageProposalResult, arguments: PageWork, step: str) -> PageReply:
    return PageReply.model_validate(
        {
            **result.model_dump(),
            "draftId": arguments.draft_id,
            "nextStep": step,
            "notices": arguments.notices(),
        }
    )


PAGE_TOOLS: tuple[Tool, ...] = (
    Tool(
        "edit_draft",
        "Build a page in a draft",
        EDIT_DESCRIPTION,
        EditDraft,
        DraftReply,
        _edit_draft,
        CONTRIBUTE_SCOPE,
        WRITES,
        group=PAGES,
    ),
    Tool(
        "preview_page",
        "Preview a page",
        PREVIEW_DESCRIPTION,
        PreviewWork,
        PreviewReply,
        _preview_page,
        CONTRIBUTE_SCOPE,
        READ_ONLY,
        group=PAGES,
        view=PAGE_PREVIEW_VIEW_URI,
        records=True,
        shows_output=True,
    ),
    Tool(
        "propose_page",
        "Propose a page or one of its parts",
        PROPOSE_DESCRIPTION,
        PageWork,
        PageReply,
        _propose_page,
        CONTRIBUTE_SCOPE,
        WRITES,
        group=PAGES,
    ),
)
