from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import release_connection
from app.models import User
from app.research.monograph_document import MonographDocument
from app.research.page_proposals import PagePreviewResult
from app.research.page_render import RenderedImage, RenderRequest, RenderResult, kept_images, render_plan
from app.research.page_report import PageReport
from app.research.page_report_drawing import drawing_report, with_drawing

from .page_preview_links import issued_pass, preview_document, preview_token
from .page_renders import PageRenderer, record_drawing

__all__ = ["DrawnPreview", "drawn_preview"]


@dataclass(frozen=True)
class DrawnPreview:
    report: PageReport | None
    images: list[RenderedImage] = field(default_factory=list)


async def drawn_preview(
    session: AsyncSession,
    user: User,
    previewed: PagePreviewResult,
    report: PageReport | None,
    *,
    renderer: PageRenderer,
    now: datetime,
) -> DrawnPreview:
    if report is None:
        return DrawnPreview(report=None)
    stored = await preview_document(session, user, preview_token(previewed.preview_url), now=now)
    request = RenderRequest(
        preview_url=previewed.preview_url,
        render_pass=issued_pass(previewed.preview_url, user, now=now),
        plan=render_plan(MonographDocument.model_validate(stored)),
    )
    await release_connection(session)
    outcome = await renderer.render(request)
    drawing = drawing_report(outcome)
    await record_drawing(session, user, previewed.preview_url, drawing, now=now)
    images = kept_images(outcome.images) if isinstance(outcome, RenderResult) else []
    return DrawnPreview(report=with_drawing(report, drawing), images=images)
