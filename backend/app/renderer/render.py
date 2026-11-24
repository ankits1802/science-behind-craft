from __future__ import annotations

import asyncio
import json
import time
from dataclasses import dataclass

from app.data.drawing_checks import DRAWING_KIT
from app.research.page_render import (
    BROWSER,
    CHAPTER_SCALE,
    CHAPTER_VIEW_HEIGHT,
    CHAPTERS_SHOWN_MAX,
    DESKTOP_WIDTH,
    IMAGE_BYTES_MAX,
    WIDTHS,
    DrawnProblem,
    RenderedImage,
    RenderRequest,
    RenderResult,
    image_bytes,
    kept_images,
)

from .browser import launched
from .cdp import Cdp, CdpError, Message
from .failures import RenderFailed
from .guard import RequestGuard
from .tab import SCROLL_SECONDS, Tab

__all__ = ["BLOCKED_MAX", "BrowserRenderer", "rendered"]

BLOCKED_MAX = 20
CHAPTER_CAPTION = "Chapter {key} at 1440 px wide: its first {height} px, at two fifths of their size"
BROWSER_FAILED = "the browser failed while it drew the page: {error}"


@dataclass(frozen=True)
class BrowserRenderer:
    browser: str
    site: str

    async def render(self, request: RenderRequest) -> RenderResult:
        guard = RequestGuard(site=self.site, preview_url=request.preview_url)
        try:
            async with launched(self.browser, site=self.site) as cdp:
                return await rendered(cdp, request, guard)
        except CdpError as failed:
            raise RenderFailed(BROWSER, BROWSER_FAILED.format(error=failed)) from None


async def rendered(cdp: Cdp, request: RenderRequest, guard: RequestGuard) -> RenderResult:
    started = time.monotonic()
    tab = await Tab.opened(cdp, guard, request.render_pass)
    problems: list[DrawnProblem] = []
    images: list[RenderedImage] = []
    for width in WIDTHS:
        problems += await tab.reviewed(width, request.preview_url, request.plan)
        images.append(await tab.first_screen(width))
    images += await chapter_shots(tab, request.plan.chapters, spent=sum(map(image_bytes, images)))
    return RenderResult(
        problems=problems,
        images=kept_images(images),
        blocked=sorted(guard.blocked)[:BLOCKED_MAX],
        seconds=round(time.monotonic() - started, 1),
    )


async def chapter_shots(tab: Tab, keys: list[str], *, spent: int) -> list[RenderedImage]:
    await tab.sized(DESKTOP_WIDTH, CHAPTER_VIEW_HEIGHT)
    await asyncio.sleep(SCROLL_SECONDS)
    found = await tab.evaluate(f"{DRAWING_KIT}.chapters({json.dumps(keys)})")
    shots: list[RenderedImage] = []
    for chapter in found[:CHAPTERS_SHOWN_MAX]:
        shot = await _chapter(tab, chapter)
        if shot is None:
            continue
        size = image_bytes(shot)
        if spent + size > IMAGE_BYTES_MAX:
            break
        spent += size
        shots.append(shot)
    return shots


async def _chapter(tab: Tab, chapter: Message) -> RenderedImage | None:
    top = int(chapter["top"])
    scrolled = int(await tab.evaluate(f"(window.scrollTo(0, {top}), window.scrollY)"))
    await asyncio.sleep(SCROLL_SECONDS)
    height = min(int(chapter["height"]), scrolled + CHAPTER_VIEW_HEIGHT - top)
    if height < 1:
        return None
    data = await tab.shot(
        {"x": 0, "y": top, "width": DESKTOP_WIDTH, "height": height, "scale": CHAPTER_SCALE}
    )
    return RenderedImage(
        name=f"chapter-{chapter['key']}",
        caption=CHAPTER_CAPTION.format(key=chapter["key"], height=height),
        width=round(DESKTOP_WIDTH * CHAPTER_SCALE),
        height=max(1, round(height * CHAPTER_SCALE)),
        data=data,
    )
