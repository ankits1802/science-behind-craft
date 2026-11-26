from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import release_connection
from app.models import User
from app.research.monograph_document import MonographDocument
from app.research.page_proposal_review import PageDrawing
from app.research.page_render import RenderRequest, RenderUnmade, kept_images, render_plan
from app.research.page_report_drawing import problem_line

from .page_preview_links import issued_pass, preview_path, store_preview
from .page_proposal_pictures import picture_views, store_side
from .page_proposal_reviews import proposal_document
from .page_renders import PageRenderer

__all__ = ["DRAWN", "NOT_DRAWN", "draw_side"]

DRAWN = "Drawn by the site's renderer at 390 and 1440 px: {count} pictures kept, {problems} drawing problems found."
NOT_DRAWN = "The renderer did not draw it: {reason} The pictures kept before stay as they were."


async def draw_side(
    session: AsyncSession,
    reviewer: User,
    proposal_id: uuid.UUID,
    side: str,
    *,
    renderer: PageRenderer,
    site: str,
    now: datetime,
) -> PageDrawing:
    document = MonographDocument.model_validate(await proposal_document(session, reviewer, proposal_id, side))
    _, token = await store_preview(session, reviewer, document, now=now)
    url = f"{site}{preview_path(token)}"
    request = RenderRequest(
        preview_url=url, render_pass=issued_pass(url, reviewer, now=now), plan=render_plan(document)
    )
    await release_connection(session)
    outcome = await renderer.render(request)
    if isinstance(outcome, RenderUnmade):
        kept = [view for view in await picture_views(session, proposal_id) if view.side == side]
        return PageDrawing(
            side=side, drawn=False, message=NOT_DRAWN.format(reason=outcome.message), pictures=kept
        )
    images = kept_images(outcome.images)
    await store_side(session, proposal_id, side, images)
    shown = [view for view in await picture_views(session, proposal_id) if view.side == side]
    problems = [problem_line(problem) for problem in outcome.problems]
    return PageDrawing(
        side=side,
        drawn=True,
        message=DRAWN.format(count=len(shown), problems=len(problems)),
        pictures=shown,
        problems=problems,
    )
