from __future__ import annotations

import uuid
from datetime import datetime
from typing import Protocol

import httpx
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.errors import InvalidInput
from app.models import PagePreview, User
from app.research.page_render import (
    BROWSER,
    FAILED,
    QUEUE_SECONDS,
    RENDER_SECONDS,
    RENDERER_PATH,
    TIMEOUT,
    UNREACHABLE,
    DrawingReport,
    DrawnProblem,
    RenderRequest,
    RenderResult,
    RenderUnmade,
)
from app.research.page_report_drawing import problem_line

from .open_work_subjects import WorkSubject
from .page_preview_links import preview_key, preview_token, token_preview

__all__ = [
    "RENDER_CLIENT_SECONDS",
    "PageRenderer",
    "RendererClient",
    "drawing_refusal",
    "page_renderer",
    "record_drawing",
    "refuse_a_failed_drawing",
]

RENDER_CLIENT_SECONDS = RENDER_SECONDS + QUEUE_SECONDS + 5.0
REFUSAL_LINES_MAX = 5
NOT_RUNNING = "the renderer is not running on the API's box just now."
NO_ANSWER = "the renderer did not answer within {seconds:g} s."
OFF_CONTRACT = "the renderer answered {status} with a body off its contract."
REFUSAL = (
    "The latest preview of {kind} {slug} failed its drawing checks (rule 28 of the page checklist): {lines}. "
    "Fix each one, call preview_page again and look at its pictures; propose_page takes the page once its "
    "latest preview no longer fails them."
)


class PageRenderer(Protocol):
    async def render(self, request: RenderRequest) -> RenderResult | RenderUnmade: ...


class RendererClient:
    def __init__(
        self,
        base_url: str,
        *,
        seconds: float = RENDER_CLIENT_SECONDS,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.endpoint = base_url.rstrip("/") + RENDERER_PATH
        self.seconds = seconds
        self.transport = transport

    async def render(self, request: RenderRequest) -> RenderResult | RenderUnmade:
        try:
            async with httpx.AsyncClient(timeout=self.seconds, transport=self.transport) as client:
                response = await client.post(self.endpoint, json=request.model_dump(mode="json"))
        except httpx.TimeoutException:
            return RenderUnmade(reason=TIMEOUT, message=NO_ANSWER.format(seconds=self.seconds))
        except httpx.HTTPError:
            return RenderUnmade(reason=UNREACHABLE, message=NOT_RUNNING)
        return _outcome(response)


def page_renderer() -> PageRenderer:
    return RendererClient(get_settings().renderer_url)


async def record_drawing(
    session: AsyncSession, user: User, preview_url: str, drawing: DrawingReport, *, now: datetime
) -> None:
    preview_id = token_preview(preview_token(preview_url), user.id, preview_key(), now=now)
    row = await session.get(PagePreview, preview_id)
    if row is None:
        return
    row.drawing = drawing.state
    row.drawingProblems = [problem.model_dump(mode="json") for problem in drawing.problems]
    await session.flush()


async def drawing_refusal(
    session: AsyncSession, user_id: uuid.UUID, subject: WorkSubject, *, now: datetime
) -> str | None:
    row = await session.scalar(
        select(PagePreview)
        .where(
            PagePreview.userId == user_id,
            PagePreview.subjectKind == subject.kind,
            PagePreview.subjectSlug == subject.slug,
            PagePreview.expiresAt > now,
        )
        .order_by(PagePreview.createdAt.desc())
        .limit(1)
    )
    if row is None or row.drawing != FAILED:
        return None
    problems = [DrawnProblem.model_validate(item) for item in row.drawingProblems or []]
    lines = "; ".join(problem_line(problem) for problem in problems[:REFUSAL_LINES_MAX])
    return REFUSAL.format(
        kind=subject.kind, slug=subject.slug, lines=lines or "the problems its report named"
    )


async def refuse_a_failed_drawing(
    session: AsyncSession, user_id: uuid.UUID, subject: WorkSubject, *, now: datetime
) -> None:
    refusal = await drawing_refusal(session, user_id, subject, now=now)
    if refusal is not None:
        raise InvalidInput(refusal)


def _outcome(response: httpx.Response) -> RenderResult | RenderUnmade:
    try:
        if response.status_code == httpx.codes.OK:
            return RenderResult.model_validate_json(response.content)
        return RenderUnmade.model_validate_json(response.content)
    except ValidationError:
        return RenderUnmade(reason=BROWSER, message=OFF_CONTRACT.format(status=response.status_code))
