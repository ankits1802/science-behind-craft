import json
import uuid
from datetime import UTC, datetime, timedelta

import httpx
import pytest

from app.research.page_render import RenderPlan, RenderRequest, RenderResult, RenderUnmade
from app.services.page_preview_links import (
    RENDER_PASS_LIFETIME,
    UnknownPreview,
    preview_key,
    preview_token,
    render_key,
    signed_token,
    token_preview,
)
from app.services.page_renders import RENDER_CLIENT_SECONDS, RendererClient, page_renderer

TOKEN = f"{'a' * 32}.1795000000.{'b' * 64}"
REQUEST = RenderRequest(
    preview_url=f"https://kalavigyan.example/preview/{TOKEN}",
    render_pass=f"{'c' * 32}.1795000000.{'d' * 64}",
    plan=RenderPlan(components=[]),
)
PREVIEW = uuid.UUID("7b000000-0000-4000-8000-000000000001")
OWNER = uuid.UUID("7b000000-0000-4000-8000-000000000002")
NOW = datetime(2026, 11, 24, 12, 0, tzinfo=UTC)


def answering(handler: httpx.MockTransport) -> RendererClient:
    return RendererClient("http://127.0.0.1:8091", transport=handler)


async def test_a_drawn_page_comes_back_whole_from_the_renderer_s_own_address() -> None:
    sent: list[httpx.Request] = []

    def drawn(request: httpx.Request) -> httpx.Response:
        sent.append(request)
        return httpx.Response(200, json={"problems": [], "images": [], "blocked": [], "seconds": 9.5})

    outcome = await answering(httpx.MockTransport(drawn)).render(REQUEST)
    assert outcome == RenderResult(problems=[], images=[], seconds=9.5)
    assert str(sent[0].url) == "http://127.0.0.1:8091/render"
    assert json.loads(sent[0].content)["previewUrl"] == REQUEST.preview_url


async def test_a_renderer_that_could_not_draw_says_why() -> None:
    def busy(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            503, json={"reason": "BUSY", "message": "the renderer was drawing another preview"}
        )

    def garbled(request: httpx.Request) -> httpx.Response:
        return httpx.Response(502, text="<html>Bad gateway</html>")

    assert await answering(httpx.MockTransport(busy)).render(REQUEST) == RenderUnmade(
        reason="BUSY", message="the renderer was drawing another preview"
    )
    assert await answering(httpx.MockTransport(garbled)).render(REQUEST) == RenderUnmade(
        reason="BROWSER", message="the renderer answered 502 with a body off its contract."
    )


async def test_a_renderer_that_is_down_or_slow_never_stops_the_report() -> None:
    def down(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("refused", request=request)

    def slow(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("slow", request=request)

    assert await answering(httpx.MockTransport(down)).render(REQUEST) == RenderUnmade(
        reason="UNREACHABLE", message="the renderer is not running on the API's box just now."
    )
    assert await answering(httpx.MockTransport(slow)).render(REQUEST) == RenderUnmade(
        reason="TIMEOUT", message="the renderer did not answer within 45 s."
    )
    assert RENDER_CLIENT_SECONDS == 45.0


def test_the_api_reaches_the_renderer_on_the_box_by_default() -> None:
    renderer = page_renderer()
    assert isinstance(renderer, RendererClient) and renderer.endpoint == "http://127.0.0.1:8091/render"


def test_a_render_pass_lives_two_minutes_and_is_signed_with_a_key_of_its_own() -> None:
    assert timedelta(minutes=2) == RENDER_PASS_LIFETIME
    assert render_key() != preview_key()
    render_pass = signed_token(PREVIEW, OWNER, NOW + RENDER_PASS_LIFETIME, render_key())
    assert token_preview(render_pass, OWNER, render_key(), now=NOW) == PREVIEW
    with pytest.raises(UnknownPreview):
        token_preview(render_pass, OWNER, preview_key(), now=NOW)
    link = signed_token(PREVIEW, OWNER, NOW + timedelta(hours=24), preview_key())
    with pytest.raises(UnknownPreview):
        token_preview(link, OWNER, render_key(), now=NOW)
    with pytest.raises(UnknownPreview):
        token_preview(render_pass, OWNER, render_key(), now=NOW + RENDER_PASS_LIFETIME)


def test_a_preview_s_token_is_read_from_its_link() -> None:
    assert preview_token(f"https://kalavigyan.example/preview/{TOKEN}") == TOKEN
