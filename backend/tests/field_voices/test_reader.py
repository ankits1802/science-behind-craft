from typing import Any

import httpx
import pytest

from app.core.errors import ExternalFailure, InvalidInput, NotConfigured, Refused
from app.services.field_voices_feed import Live
from app.services.field_voices_items import TranscriptItem
from app.services.field_voices_reader import FieldVoicesReader, field_voices_reader
from app.services.field_voices_screen import PortalScreen
from tests.field_voices.fixtures import (
    DR,
    FR,
    Answers,
    edited,
    enabled_settings,
    portal_transport,
    recorded_answers,
    resigned,
)
from tests.portal_sync.fixtures import TOKEN, settings

TRANSCRIPTS_ALL = ("/field-voices/transcripts", "all", None)


def reader(portal: str, answers: Answers, **transport: Any) -> FieldVoicesReader:
    return field_voices_reader(enabled_settings(), portal, transport=portal_transport(answers, **transport))


def test_the_reader_is_off_until_the_setting_is_on() -> None:
    with pytest.raises(NotConfigured) as caught:
        field_voices_reader(settings(), FR, transport=portal_transport(recorded_answers(FR)))
    assert caught.value.name == "FIELD_VOICES_ENABLED"


@pytest.mark.parametrize(
    "hosts", [None, " , ", "https://media.example.com", "media.example.com/field-voices"]
)
def test_the_reader_needs_the_image_hosts_named(hosts: str | None) -> None:
    configured = settings(FIELD_VOICES_ENABLED=True, FIELD_VOICES_IMAGE_HOSTS=hosts)
    with pytest.raises(NotConfigured) as caught:
        field_voices_reader(configured, DR, transport=portal_transport(recorded_answers(DR)))
    assert caught.value.name == "FIELD_VOICES_IMAGE_HOSTS"


@pytest.mark.parametrize(
    ("portal", "url"),
    [
        (FR, "https://field.example.com/api/cross-portal/peer/field-voices"),
        (DR, "https://designer.example.com/api/cross-portal/peer/field-voices"),
    ],
)
async def test_each_portal_is_read_with_the_peer_headers(portal: str, url: str) -> None:
    seen: list[httpx.Request] = []
    state = await reader(portal, recorded_answers(portal), seen=seen).state()
    assert state.portal == portal
    request = seen[0]
    assert str(request.url) == url
    assert request.headers["authorization"] == f"Bearer {TOKEN}"
    assert len(request.headers["x-cross-portal-nonce"]) == 32
    assert request.headers["x-cross-portal-requested-by"] == "kalavigyan-field-voices"


async def test_a_page_is_asked_for_by_stream_view_and_cursor() -> None:
    seen: list[httpx.Request] = []
    page = await reader(FR, recorded_answers(FR), seen=seen).page(
        "transcripts", "all", "fr-t-2", screen=PortalScreen()
    )
    assert [change.id for change in page.changes] == ["fr-media-2"]
    assert seen[0].url.path.endswith("/cross-portal/peer/field-voices/transcripts")
    assert dict(seen[0].url.params) == {"view": "all", "cursor": "fr-t-2"}


async def test_an_unsigned_answer_is_refused() -> None:
    answers = recorded_answers(FR)
    transport = httpx.MockTransport(
        lambda request: httpx.Response(200, json=answers[("/field-voices", None, None)])
    )
    unsigned = field_voices_reader(enabled_settings(), FR, transport=transport)
    with pytest.raises(Refused) as caught:
        await unsigned.state()
    assert caught.value.reason == "unsigned_answer"


async def test_an_answer_signed_with_another_token_is_refused() -> None:
    with pytest.raises(Refused):
        await reader(FR, recorded_answers(FR), token="z" * 40).state()


async def test_a_portal_with_the_gate_off_answers_404() -> None:
    with pytest.raises(ExternalFailure) as caught:
        await reader(FR, {}).state()
    assert caught.value.status == 404


async def test_a_busy_portal_carries_its_retry_after() -> None:
    with pytest.raises(ExternalFailure) as caught:
        await reader(FR, recorded_answers(FR), status=503).state()
    assert caught.value.retryable


async def test_an_image_from_an_unlisted_host_is_refused() -> None:
    def moved(page: dict[str, Any]) -> None:
        image = page["changes"][0]["image"]
        image["url"] = image["url"].replace("fieldrepo-media-626159998512", "elsewhere-media")

    answers = edited(recorded_answers(FR), ("/field-voices/images", "all", None), moved)
    with pytest.raises(InvalidInput, match="FIELD_VOICES_IMAGE_HOSTS"):
        await reader(FR, answers).page("images", "all", None, screen=PortalScreen())


async def test_personal_data_the_portal_missed_is_scrubbed_and_counted() -> None:
    def leak(page: dict[str, Any]) -> None:
        change = page["changes"][0]
        change["transcript"]["segments"][3]["text"] = "Ring 98250 12345 or write to asha@example.com today."
        change["workshop"]["title"] = "Visit, call 98250 12345"
        resigned(change)

    answers = edited(recorded_answers(FR), TRANSCRIPTS_ALL, leak)
    screen = PortalScreen()
    page = await reader(FR, answers).page("transcripts", "all", None, screen=screen)
    live = page.changes[0]
    assert isinstance(live, Live) and isinstance(live.item, TranscriptItem)
    assert live.item.transcript.segments[3].text == "Ring [number] or write to [email] today."
    assert live.item.workshop is not None and live.item.workshop.title is None
    assert screen.misses == 2


async def test_a_leaking_speaker_label_becomes_a_numbered_speaker() -> None:
    def leak(page: dict[str, Any]) -> None:
        change = page["changes"][0]
        change["speakers"][2]["label"] = "Neighbour 9825012345"
        resigned(change)

    answers = edited(recorded_answers(FR), TRANSCRIPTS_ALL, leak)
    page = await reader(FR, answers).page("transcripts", "all", None, screen=PortalScreen())
    live = page.changes[0]
    assert isinstance(live, Live) and isinstance(live.item, TranscriptItem)
    assert live.item.speakers[2].label == "Speaker 3"
