import json
from collections.abc import Callable
from pathlib import Path

import httpx
import pytest

from app.media.output import checked_output
from app.media.prompt import REQUESTED_OUTPUT
from app.providers.base import MediaRequest, ProviderError
from app.providers.gemini_media import GeminiMediaWire
from app.providers.gemini_p import GeminiAdapter

from .fakes import png_bytes
from .mp4_builder import movie

FIXTURES = Path(__file__).parent / "fixtures"
KEY = "test-only-gemini-key"
API = "https://generativelanguage.googleapis.com/v1beta"
IMAGE = MediaRequest(
    model="gemini-3.1-flash-image",
    prompt="Draw one stage.",
    kind="IMAGE",
    output=dict(REQUESTED_OUTPUT["IMAGE"]),
)
VIDEO = MediaRequest(
    model="gemini-omni-1.2-flash",
    prompt="Show one stage.",
    kind="VIDEO",
    output=dict(REQUESTED_OUTPUT["VIDEO"]),
)


def fixture(name: str) -> bytes:
    return (FIXTURES / name).read_bytes()


class Recorder:
    def __init__(self, answer: Callable[[httpx.Request], httpx.Response]) -> None:
        self.requests: list[httpx.Request] = []
        self._answer = answer

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        return self._answer(request)

    def wire(self) -> GeminiMediaWire:
        return GeminiMediaWire(api_key=KEY, client=httpx.AsyncClient(transport=httpx.MockTransport(self)))


def answering(name: str, status: int = 200, headers: dict | None = None) -> Recorder:
    return Recorder(lambda _: httpx.Response(status, content=fixture(name), headers=headers))


async def test_an_image_is_one_synchronous_unstored_interaction() -> None:
    recorder = answering("image_completed.json")
    result = await recorder.wire().generate_image(IMAGE)
    sent = recorder.requests[0]
    assert (sent.method, str(sent.url)) == ("POST", f"{API}/interactions")
    assert sent.headers["x-goog-api-key"] == KEY
    assert sent.headers["api-revision"] == "2026-05-20"
    assert json.loads(sent.content) == {
        "model": "gemini-3.1-flash-image",
        "input": "Draw one stage.",
        "response_format": {"type": "image", "aspect_ratio": "1:1", "image_size": "1K"},
        "background": False,
        "store": False,
    }
    assert result.data == png_bytes(1024, 1024)
    assert (result.mime, result.input_tokens, result.output_tokens, result.media_tokens) == (
        "image/png",
        312,
        1180,
        1120,
    )
    assert result.provider_ref == "v1_ChdpbWFnZS1pbnRlcmFjdGlvbi0wMDAx"
    stored = checked_output("IMAGE", result)
    assert (stored.width, stored.height, stored.duration_seconds) == (1024, 1024, None)


async def test_a_video_starts_in_the_background_and_is_polled_until_done() -> None:
    answers = iter(["video_started.json", "video_started.json", "video_completed.json"])
    recorder = Recorder(lambda _: httpx.Response(200, content=fixture(next(answers))))
    wire = recorder.wire()
    ref = await wire.start_video(VIDEO)
    assert json.loads(recorder.requests[0].content)["background"] is True
    assert "store" not in json.loads(recorder.requests[0].content)
    assert json.loads(recorder.requests[0].content)["response_format"] == {
        "type": "video",
        "aspect_ratio": "16:9",
        "resolution": "720p",
        "duration": "8s",
    }
    first = await wire.poll_video(ref)
    done = await wire.poll_video(ref)
    assert not first.done and done.done and done.result is not None
    assert str(recorder.requests[1].url) == f"{API}/interactions/v1_ChdvbW5pLWludGVyYWN0aW9uLTAwMDM"
    assert done.result.data == movie().data
    assert done.result.media_tokens == 46336
    stored = checked_output("VIDEO", done.result)
    assert (stored.width, stored.height, stored.duration_seconds) == (1280, 720, 8.0)
    assert b"soun" not in stored.data


async def test_a_video_delivered_by_uri_is_downloaded_from_the_files_api() -> None:
    clip = movie().data

    def answer(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith(":download"):
            return httpx.Response(200, content=clip)
        return httpx.Response(200, content=fixture("video_completed_uri.json"))

    recorder = Recorder(answer)
    poll = await recorder.wire().poll_video("v1_ChdvbW5pLWludGVyYWN0aW9uLTAwMDQ")
    assert poll.result is not None and poll.result.data == clip
    download = recorder.requests[1]
    assert str(download.url) == f"{API}/files/omni-clip-0004:download?alt=media"
    assert download.headers["x-goog-api-key"] == KEY


@pytest.mark.parametrize(
    ("call", "name", "status", "kind"),
    [
        ("image", "image_text_only.json", 200, "refusal"),
        ("image", "error_400_policy.json", 400, "refusal"),
        ("poll", "video_failed_safety.json", 200, "refusal"),
        ("image", "error_429.json", 429, "rate_limit"),
    ],
)
async def test_refusals_and_limits_map_to_the_shared_kinds(
    call: str, name: str, status: int, kind: str
) -> None:
    wire = answering(name, status, {"Retry-After": "7"} if status == 429 else None).wire()
    with pytest.raises(ProviderError) as failure:
        await (wire.generate_image(IMAGE) if call == "image" else wire.poll_video("v1_x"))
    assert failure.value.kind == kind
    assert KEY not in str(failure.value)
    if status == 429:
        assert failure.value.retry_after == 7.0 and failure.value.retryable


async def test_a_uri_outside_the_files_api_is_never_fetched_with_the_key() -> None:
    body = json.loads(fixture("video_completed_uri.json"))
    body["steps"][0]["content"][0]["uri"] = "https://example.com/clip.mp4"
    recorder = Recorder(lambda _: httpx.Response(200, json=body))
    with pytest.raises(ProviderError, match="outside the Files API"):
        await recorder.wire().poll_video("v1_y")
    assert len(recorder.requests) == 1


async def test_the_gemini_adapter_reaches_the_wire_with_its_key() -> None:
    recorder = answering("image_completed.json")
    client = httpx.AsyncClient(transport=httpx.MockTransport(recorder))
    adapter = GeminiAdapter(
        api_key=KEY, base_url=None, preset="gemini", extra={}, learned={}, media_client=client
    )
    result = await adapter.generate_image(IMAGE)
    await adapter.aclose()
    assert result.mime == "image/png"
    assert recorder.requests[0].headers["x-goog-api-key"] == KEY
