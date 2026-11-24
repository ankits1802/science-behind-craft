from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlsplit

from app.data.drawing_checks import DRAWING_KIT, drawing_checks
from app.research.page_render import (
    BROWSER,
    ELSEWHERE,
    FIRST_SCREEN_SCALES,
    JPEG_QUALITY,
    PHONE_WIDTH,
    RENDER_PASS_HEADER,
    TIMEOUT,
    VIEW_HEIGHTS,
    DrawnProblem,
    RenderedImage,
    RenderPlan,
)

from .cdp import Cdp, Message
from .failures import RenderFailed
from .guard import ALLOW, PASS, RequestGuard

__all__ = ["NAVIGATION_SECONDS", "Tab"]

NAVIGATION_SECONDS = 20.0
SETTLE_MS = 5000
REST_SECONDS = 1.0
SCROLL_SECONDS = 0.15
BLOCKED_REASON = "BlockedByClient"
LIGHT_AT_REST = [
    {"name": "prefers-color-scheme", "value": "light"},
    {"name": "prefers-reduced-motion", "value": "reduce"},
]
LANDED = "({href: location.href, status: (performance.getEntriesByType('navigation')[0] || {}).responseStatus || 0})"
FIRST_CAPTION = "The first screen at {width} px wide, as a reader opens the page"
NOT_OPENED = "the preview page did not open ({error}): it may have sent the renderer to sign in"
SLOW_PAGE = "the preview page did not finish loading within {seconds} s"
SENT_ELSEWHERE = "the preview page sent the renderer to {path} instead of drawing"
ANSWERED = "the preview page answered {status}: the preview may have expired; call preview_page again"
STOPPED = "the page's drawing checks stopped: {error}"


@dataclass
class Tab:
    cdp: Cdp
    session: str
    guard: RequestGuard
    render_pass: str

    @classmethod
    async def opened(cls, cdp: Cdp, guard: RequestGuard, render_pass: str) -> Tab:
        target = await cdp.send("Target.createTarget", {"url": "about:blank"})
        attached = await cdp.send("Target.attachToTarget", {"targetId": target["targetId"], "flatten": True})
        tab = cls(cdp, str(attached["sessionId"]), guard, render_pass)
        cdp.on("Fetch.requestPaused", tab.paused)
        await tab.call("Fetch.enable", {"patterns": [{"urlPattern": "*", "requestStage": "Request"}]})
        await tab.call("Page.enable")
        await tab.call("Emulation.setEmulatedMedia", {"media": "screen", "features": LIGHT_AT_REST})
        return tab

    async def call(self, method: str, params: Message | None = None) -> Message:
        return await self.cdp.send(method, params, session=self.session)

    async def paused(self, params: Message, session: str | None) -> None:
        if session != self.session:
            return
        request: Message = params.get("request") or {}
        verdict = self.guard.decide(str(request.get("url", "")), str(params.get("resourceType", "")))
        ident = params["requestId"]
        if verdict == PASS:
            headers = [
                {"name": name, "value": value} for name, value in (request.get("headers") or {}).items()
            ]
            headers.append({"name": RENDER_PASS_HEADER, "value": self.render_pass})
            await self.call("Fetch.continueRequest", {"requestId": ident, "headers": headers})
        elif verdict == ALLOW:
            await self.call("Fetch.continueRequest", {"requestId": ident})
        else:
            await self.call("Fetch.failRequest", {"requestId": ident, "errorReason": BLOCKED_REASON})

    async def evaluate(self, expression: str, *, wait: bool = False) -> Any:
        answer = await self.call(
            "Runtime.evaluate", {"expression": expression, "returnByValue": True, "awaitPromise": wait}
        )
        details = answer.get("exceptionDetails")
        if details is not None:
            error = (details.get("exception") or {}).get("description") or details.get("text") or "an error"
            raise RenderFailed(BROWSER, STOPPED.format(error=str(error)[:200]))
        return (answer.get("result") or {}).get("value")

    async def sized(self, width: int, height: int) -> None:
        metrics = {"width": width, "height": height, "deviceScaleFactor": 1, "mobile": width == PHONE_WIDTH}
        await self.call("Emulation.setDeviceMetricsOverride", metrics)

    async def open_at(self, width: int, url: str) -> None:
        await self.sized(width, VIEW_HEIGHTS[width])
        loaded = self.cdp.expect("Page.loadEventFired", self.session)
        navigated = await self.call("Page.navigate", {"url": url})
        if navigated.get("errorText"):
            loaded.cancel()
            raise RenderFailed(ELSEWHERE, NOT_OPENED.format(error=navigated["errorText"]))
        try:
            await asyncio.wait_for(loaded, NAVIGATION_SECONDS)
        except TimeoutError:
            raise RenderFailed(TIMEOUT, SLOW_PAGE.format(seconds=int(NAVIGATION_SECONDS))) from None
        landed = await self.evaluate(LANDED)
        if landed["href"] != url:
            raise RenderFailed(ELSEWHERE, SENT_ELSEWHERE.format(path=urlsplit(str(landed["href"])).path))
        if landed["status"] and landed["status"] != 200:
            raise RenderFailed(ELSEWHERE, ANSWERED.format(status=landed["status"]))

    async def reviewed(self, width: int, url: str, plan: RenderPlan) -> list[DrawnProblem]:
        await self.open_at(width, url)
        await self.evaluate(drawing_checks())
        await self.evaluate(f"{DRAWING_KIT}.settle({SETTLE_MS})", wait=True)
        await asyncio.sleep(REST_SECONDS)
        given = json.dumps(plan.model_dump(mode="json"))
        found = await self.evaluate(f"{DRAWING_KIT}.review({given})")
        return [
            DrawnProblem(width=width, label=str(item["label"]), problem=str(item["problem"]))
            for item in found["problems"]
        ]

    async def shot(self, clip: Message) -> str:
        answer = await self.call(
            "Page.captureScreenshot", {"format": "jpeg", "quality": JPEG_QUALITY, "clip": clip}
        )
        return str(answer["data"])

    async def first_screen(self, width: int) -> RenderedImage:
        await self.evaluate("window.scrollTo(0, 0)")
        await asyncio.sleep(SCROLL_SECONDS)
        height, scale = VIEW_HEIGHTS[width], FIRST_SCREEN_SCALES[width]
        data = await self.shot({"x": 0, "y": 0, "width": width, "height": height, "scale": scale})
        return RenderedImage(
            name=f"first-screen-{width}",
            caption=FIRST_CAPTION.format(width=width),
            width=round(width * scale),
            height=round(height * scale),
            data=data,
        )
