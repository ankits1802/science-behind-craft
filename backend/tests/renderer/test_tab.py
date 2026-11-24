import asyncio
import base64
import json
import re
from collections.abc import Callable
from typing import Any

import pytest

from app.data.drawing_checks import DRAWING_KIT
from app.renderer import render as render_module, tab as tab_module
from app.renderer.failures import RenderFailed
from app.renderer.guard import RequestGuard
from app.renderer.render import chapter_shots
from app.renderer.tab import LANDED, Tab
from app.research.page_render import (
    IMAGE_BYTES_MAX,
    RENDER_PASS_HEADER,
    DrawnProblem,
    RenderedComponent,
    RenderPlan,
)

SITE = "https://kalavigyan.example"
TOKEN = f"{'a' * 32}.1795000000.{'b' * 64}"
PREVIEW = f"{SITE}/preview/{TOKEN}"
PASS = f"{'c' * 32}.1795000000.{'d' * 64}"
SHOT = base64.b64encode(b"z" * 100).decode("ascii")

Answer = dict[str, Any] | Callable[[dict[str, Any]], dict[str, Any]]


class FakeCdp:
    def __init__(self, answers: dict[str, Answer]) -> None:
        self.answers = answers
        self.sent: list[tuple[str, dict[str, Any] | None, str | None]] = []

    def on(self, method: str, handler: Any) -> None:
        pass

    def expect(self, method: str, session: str | None) -> asyncio.Future[dict[str, Any]]:
        future: asyncio.Future[dict[str, Any]] = asyncio.get_running_loop().create_future()
        future.set_result({})
        return future

    async def send(
        self, method: str, params: dict[str, Any] | None = None, *, session: str | None = None
    ) -> Any:
        self.sent.append((method, params, session))
        answer = self.answers.get(method, {})
        return answer(params or {}) if callable(answer) else answer

    def calls(self, method: str) -> list[dict[str, Any]]:
        return [params or {} for sent, params, _ in self.sent if sent == method]


def tab_on(cdp: FakeCdp) -> Tab:
    return Tab(cdp, "S1", RequestGuard(site=SITE, preview_url=PREVIEW), PASS)


def page(
    landed: dict[str, Any], review: dict[str, Any] | None = None
) -> Callable[[dict[str, Any]], dict[str, Any]]:
    def evaluate(params: dict[str, Any]) -> dict[str, Any]:
        expression = str(params["expression"])
        if expression == LANDED:
            return {"result": {"value": landed}}
        if expression.startswith(f"{DRAWING_KIT}.review(") and review is not None:
            return {"result": {"value": review}}
        return {"result": {}}

    return evaluate


@pytest.fixture(autouse=True)
def no_waiting(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(tab_module, "REST_SECONDS", 0)
    monkeypatch.setattr(tab_module, "SCROLL_SECONDS", 0)
    monkeypatch.setattr(render_module, "SCROLL_SECONDS", 0)


async def test_a_request_to_the_site_carries_the_pass_a_picture_goes_bare_and_the_rest_is_refused() -> None:
    cdp = FakeCdp({})
    tab = tab_on(cdp)
    site = {
        "requestId": "1",
        "resourceType": "Script",
        "request": {"url": f"{SITE}/_next/a.js", "headers": {"Accept": "*/*"}},
    }
    commons = {
        "requestId": "2",
        "resourceType": "Image",
        "request": {"url": "https://upload.wikimedia.org/wikipedia/commons/a/ab/x.jpg"},
    }
    elsewhere = {
        "requestId": "3",
        "resourceType": "Fetch",
        "request": {"url": "https://tracker.example/beacon"},
    }
    for paused in (site, commons, elsewhere):
        await tab.paused(paused, "S1")
    await tab.paused({**elsewhere, "requestId": "4"}, "S2")
    assert cdp.sent == [
        (
            "Fetch.continueRequest",
            {
                "requestId": "1",
                "headers": [{"name": "Accept", "value": "*/*"}, {"name": RENDER_PASS_HEADER, "value": PASS}],
            },
            "S1",
        ),
        ("Fetch.continueRequest", {"requestId": "2"}, "S1"),
        ("Fetch.failRequest", {"requestId": "3", "errorReason": "BlockedByClient"}, "S1"),
    ]


async def test_a_preview_that_does_not_open_or_sends_the_browser_away_is_not_drawn() -> None:
    refused = FakeCdp({"Page.navigate": {"errorText": "net::ERR_BLOCKED_BY_CLIENT"}})
    with pytest.raises(RenderFailed, match="did not open") as caught:
        await tab_on(refused).open_at(390, PREVIEW)
    assert caught.value.reason == "ELSEWHERE"
    away = FakeCdp({"Runtime.evaluate": page({"href": f"{SITE}/login", "status": 200})})
    with pytest.raises(RenderFailed, match="sent the renderer to /login"):
        await tab_on(away).open_at(390, PREVIEW)
    expired = FakeCdp({"Runtime.evaluate": page({"href": PREVIEW, "status": 404})})
    with pytest.raises(RenderFailed, match="answered 404"):
        await tab_on(expired).open_at(1440, PREVIEW)
    assert expired.calls("Emulation.setDeviceMetricsOverride") == [
        {"width": 1440, "height": 900, "deviceScaleFactor": 1, "mobile": False}
    ]


async def test_a_script_error_in_the_page_stops_the_drawing_with_its_words() -> None:
    broken = FakeCdp(
        {"Runtime.evaluate": {"exceptionDetails": {"exception": {"description": "TypeError: x"}}}}
    )
    with pytest.raises(RenderFailed, match="drawing checks stopped: TypeError: x") as caught:
        await tab_on(broken).evaluate("1")
    assert caught.value.reason == "BROWSER"


async def test_the_review_runs_the_shared_checks_with_the_plan_at_each_width() -> None:
    plan = RenderPlan(
        components=[RenderedComponent(label="test/fig", role="figure", placed=True)], chapters=["made"]
    )
    review = {"problems": [{"label": "test/fig", "problem": "draws empty"}], "chapters": [], "height": 900}
    cdp = FakeCdp({"Runtime.evaluate": page({"href": PREVIEW, "status": 200}, review)})
    found = await tab_on(cdp).reviewed(390, PREVIEW, plan)
    assert found == [DrawnProblem(width=390, label="test/fig", problem="draws empty")]
    expressions = [str(params["expression"]) for params in cdp.calls("Runtime.evaluate")]
    assert expressions[1].startswith("(() => {") and f"{DRAWING_KIT}.settle(5000)" in expressions
    given = re.fullmatch(rf"{re.escape(DRAWING_KIT)}\.review\((.*)\)", expressions[-1], re.DOTALL)
    assert given is not None and json.loads(given.group(1)) == plan.model_dump(mode="json")
    assert cdp.calls("Emulation.setDeviceMetricsOverride")[0]["mobile"] is True


async def test_the_first_screen_is_taken_whole_at_a_phone_and_at_half_size_on_a_desktop() -> None:
    cdp = FakeCdp({"Page.captureScreenshot": {"data": SHOT}})
    phone = await tab_on(cdp).first_screen(390)
    desktop = await tab_on(cdp).first_screen(1440)
    assert [(shot.name, shot.width, shot.height) for shot in (phone, desktop)] == [
        ("first-screen-390", 390, 844),
        ("first-screen-1440", 720, 450),
    ]
    assert [params["clip"] for params in cdp.calls("Page.captureScreenshot")] == [
        {"x": 0, "y": 0, "width": 390, "height": 844, "scale": 1.0},
        {"x": 0, "y": 0, "width": 1440, "height": 900, "scale": 0.5},
    ]


def chapters_page(found: list[dict[str, Any]]) -> Callable[[dict[str, Any]], dict[str, Any]]:
    def evaluate(params: dict[str, Any]) -> dict[str, Any]:
        expression = str(params["expression"])
        if expression.startswith(f"{DRAWING_KIT}.chapters("):
            return {"result": {"value": found}}
        scrolled = re.fullmatch(r"\(window\.scrollTo\(0, (\d+)\), window\.scrollY\)", expression)
        return {"result": {"value": int(scrolled.group(1)) if scrolled else None}}

    return evaluate


async def test_each_chapter_is_taken_from_its_top_for_one_tall_screen_at_two_fifths_size() -> None:
    found = [{"key": "made", "top": 2000, "height": 3000}, {"key": "chem", "top": 5000, "height": 800}]
    cdp = FakeCdp({"Runtime.evaluate": chapters_page(found), "Page.captureScreenshot": {"data": SHOT}})
    shots = await chapter_shots(tab_on(cdp), ["made", "chem"], spent=0)
    assert [(shot.name, shot.width, shot.height) for shot in shots] == [
        ("chapter-made", 576, 640),
        ("chapter-chem", 576, 320),
    ]
    assert [params["clip"]["height"] for params in cdp.calls("Page.captureScreenshot")] == [1600, 800]
    assert cdp.calls("Emulation.setDeviceMetricsOverride") == [
        {"width": 1440, "height": 1600, "deviceScaleFactor": 1, "mobile": False}
    ]


async def test_no_chapter_is_taken_past_the_total_the_pictures_may_weigh() -> None:
    found = [{"key": "made", "top": 2000, "height": 3000}]
    cdp = FakeCdp({"Runtime.evaluate": chapters_page(found), "Page.captureScreenshot": {"data": SHOT}})
    assert await chapter_shots(tab_on(cdp), ["made"], spent=IMAGE_BYTES_MAX - 10) == []
