from __future__ import annotations

import asyncio
import logging
from collections.abc import Mapping
from types import MappingProxyType
from typing import Protocol

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from app.research.page_render import (
    BROWSER,
    BUSY,
    ELSEWHERE,
    QUEUE_SECONDS,
    REFUSED,
    RENDER_SECONDS,
    RENDERER_HEALTH_PATH,
    RENDERER_PATH,
    TIMEOUT,
    RenderRequest,
    RenderResult,
    RenderUnmade,
)

from .failures import RenderFailed
from .guard import preview_refusal

__all__ = ["STATUSES", "Renderer", "create_app"]

STATUSES: Mapping[str, int] = MappingProxyType(
    {REFUSED: 403, BUSY: 503, TIMEOUT: 504, BROWSER: 502, ELSEWHERE: 502}
)
BUSY_TEXT = (
    "the renderer was drawing another preview for longer than {seconds:g} s; preview again in a minute"
)
LATE_TEXT = "the page was not drawn within {seconds:g} s, so the renderer stopped"

logger = logging.getLogger("kalavigyan.renderer")


class Renderer(Protocol):
    async def render(self, request: RenderRequest) -> RenderResult: ...


def create_app(
    renderer: Renderer, *, site: str, seconds: float = RENDER_SECONDS, queue: float = QUEUE_SECONDS
) -> FastAPI:
    app = FastAPI(title="KalaVigyan renderer", docs_url=None, redoc_url=None, openapi_url=None)
    gate = asyncio.Lock()

    @app.get(RENDERER_HEALTH_PATH)
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post(RENDERER_PATH)
    async def render(request: RenderRequest) -> JSONResponse:
        refusal = preview_refusal(request.preview_url, site)
        if refusal is not None:
            return _unmade(REFUSED, refusal)
        try:
            await asyncio.wait_for(gate.acquire(), queue)
        except TimeoutError:
            return _unmade(BUSY, BUSY_TEXT.format(seconds=queue))
        try:
            return await _drawn(renderer, request, seconds)
        finally:
            gate.release()

    return app


async def _drawn(renderer: Renderer, request: RenderRequest, seconds: float) -> JSONResponse:
    try:
        async with asyncio.timeout(seconds):
            result = await renderer.render(request)
    except TimeoutError:
        return _unmade(TIMEOUT, LATE_TEXT.format(seconds=seconds))
    except RenderFailed as failed:
        return _unmade(failed.reason, failed.message)
    logger.info(
        "drawn in %s s with %d problems and %d pictures",
        result.seconds,
        len(result.problems),
        len(result.images),
    )
    return JSONResponse(result.model_dump(mode="json"))


def _unmade(reason: str, message: str) -> JSONResponse:
    logger.info("not drawn: %s", reason)
    body = RenderUnmade.model_validate({"reason": reason, "message": message})
    return JSONResponse(body.model_dump(mode="json"), status_code=STATUSES[reason])
