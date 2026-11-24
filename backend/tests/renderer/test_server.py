import asyncio
from typing import Any

import httpx

from app.renderer.failures import RenderFailed
from app.renderer.server import create_app
from app.research.page_render import RenderPlan, RenderRequest, RenderResult

SITE = "https://kalavigyan.example"
TOKEN = f"{'a' * 32}.1795000000.{'b' * 64}"
PREVIEW = f"{SITE}/preview/{TOKEN}"
PASS = f"{'c' * 32}.1795000000.{'d' * 64}"
DRAWN = RenderResult(problems=[], images=[], seconds=1.0)


class Renderer:
    def __init__(self, *pauses: float, failure: RenderFailed | None = None) -> None:
        self.pauses = list(pauses)
        self.failure = failure
        self.drawn: list[str] = []

    async def render(self, request: RenderRequest) -> RenderResult:
        await asyncio.sleep(self.pauses.pop(0) if self.pauses else 0)
        if self.failure is not None:
            raise self.failure
        self.drawn.append(request.preview_url)
        return DRAWN


def body(url: str = PREVIEW) -> dict[str, Any]:
    request = RenderRequest(preview_url=url, render_pass=PASS, plan=RenderPlan(components=[]))
    return request.model_dump(mode="json")


def client(renderer: Renderer, **limits: float) -> httpx.AsyncClient:
    app = create_app(renderer, site=SITE, **limits)
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://renderer")


async def test_a_preview_is_drawn_and_its_result_returned() -> None:
    renderer = Renderer()
    async with client(renderer) as renderer_client:
        drawn = await renderer_client.post("/render", json=body())
        health = await renderer_client.get("/health")
    assert drawn.status_code == 200 and RenderResult.model_validate(drawn.json()) == DRAWN
    assert renderer.drawn == [PREVIEW] and health.json() == {"status": "ok"}


async def test_anything_but_a_preview_of_the_site_is_refused_before_a_browser_starts() -> None:
    renderer = Renderer()
    async with client(renderer) as renderer_client:
        refused = await renderer_client.post("/render", json=body("https://elsewhere.example/"))
    assert refused.status_code == 403 and refused.json()["reason"] == "REFUSED"
    assert renderer.drawn == []


async def test_a_render_past_its_time_is_stopped_and_frees_the_renderer() -> None:
    renderer = Renderer(5.0, 0.0)
    async with client(renderer, seconds=0.05) as renderer_client:
        late = await renderer_client.post("/render", json=body())
        next_one = await renderer_client.post("/render", json=body())
    assert late.status_code == 504
    assert late.json() == {
        "reason": "TIMEOUT",
        "message": "the page was not drawn within 0.05 s, so the renderer stopped",
    }
    assert next_one.status_code == 200 and renderer.drawn == [PREVIEW]


async def test_one_render_at_a_time_and_a_second_waits_only_so_long() -> None:
    renderer = Renderer(0.3)
    async with client(renderer, queue=0.05) as renderer_client:
        first, second = await asyncio.gather(
            renderer_client.post("/render", json=body()),
            renderer_client.post("/render", json=body()),
        )
    assert sorted([first.status_code, second.status_code]) == [200, 503]
    busy = first if first.status_code == 503 else second
    assert busy.json()["reason"] == "BUSY" and "longer than 0.05 s" in busy.json()["message"]


async def test_a_browser_that_fails_says_so_in_words() -> None:
    renderer = Renderer(failure=RenderFailed("BROWSER", "no browser is installed at /opt/x"))
    async with client(renderer) as renderer_client:
        failed = await renderer_client.post("/render", json=body())
    assert failed.status_code == 502
    assert failed.json() == {"reason": "BROWSER", "message": "no browser is installed at /opt/x"}
