import hashlib
from typing import Any

import httpx
import pytest

from app.core.errors import ExternalFailure, InvalidInput, NotConfigured, Refused
from app.services.field_voices_feed import FieldVoicesEntry
from app.services.field_voices_reader import FieldVoicesReader, field_voices_reader
from app.services.portal_peer import peer_for
from tests.field_voices.fixtures import (
    AJRAKH_PHOTOGRAPHS,
    AJRAKH_QUOTES,
    IMAGE_HOST,
    INDEX,
    PEER_PREFIX,
    Answers,
    ajrakh_entry,
    enabled_settings,
    portal_transport,
    recorded_answers,
)
from tests.portal_sync.fixtures import TOKEN, edited, settings


def reader(answers: Answers, **transport: Any) -> FieldVoicesReader:
    return field_voices_reader(enabled_settings(), transport=portal_transport(answers, **transport))


def entry(answers: Answers) -> FieldVoicesEntry:
    return FieldVoicesEntry.model_validate(ajrakh_entry(answers))


def test_the_reader_is_off_until_the_setting_is_on() -> None:
    with pytest.raises(NotConfigured) as caught:
        field_voices_reader(settings(), transport=portal_transport(recorded_answers()))
    assert caught.value.name == "FIELD_VOICES_ENABLED"


@pytest.mark.parametrize(
    "hosts", [None, " , ", "https://media.example.com", "media.example.com/field-voices"]
)
def test_the_reader_needs_the_image_hosts_named(hosts: str | None) -> None:
    configured = settings(FIELD_VOICES_ENABLED=True, FIELD_VOICES_IMAGE_HOSTS=hosts)
    with pytest.raises(NotConfigured) as caught:
        field_voices_reader(configured, transport=portal_transport(recorded_answers()))
    assert caught.value.name == "FIELD_VOICES_IMAGE_HOSTS"


async def test_the_index_is_read_with_the_peer_headers() -> None:
    seen: list[httpx.Request] = []
    index = await reader(recorded_answers(), seen=seen).index()
    assert [c.craft_slug for c in index.crafts] == ["Kutch-Ajrakh", "Dabu-Print"]
    request = seen[0]
    assert str(request.url) == "https://field.example.com/api/cross-portal/peer/field-voices"
    assert request.headers["authorization"] == f"Bearer {TOKEN}"
    assert len(request.headers["x-cross-portal-nonce"]) == 32
    assert request.headers["x-cross-portal-requested-by"] == "kalavigyan-field-voices"


async def test_a_craft_is_read_across_its_pages_and_checked_against_the_index() -> None:
    answers = recorded_answers()
    seen: list[httpx.Request] = []
    voices = await reader(answers, seen=seen).craft(entry(answers))
    asked = [(r.url.path.removeprefix(f"/api{PEER_PREFIX}"), r.url.params.get("cursor")) for r in seen]
    assert asked == [(AJRAKH_QUOTES, None), (AJRAKH_QUOTES, "c2"), (AJRAKH_PHOTOGRAPHS, None)]
    assert [r.id for r in voices.recordings] == ["rec-1", "rec-2"]
    assert [p.id for p in voices.photographs] == ["photo-1"]
    assert voices.dropped == ()
    assert voices.digest == ajrakh_entry(answers)["digest"]


async def test_an_unsigned_page_is_refused() -> None:
    answers = recorded_answers()
    transport = httpx.MockTransport(lambda request: httpx.Response(200, json=answers[(INDEX, None)]))
    unsigned = field_voices_reader(enabled_settings(), transport=transport)
    with pytest.raises(Refused) as caught:
        await unsigned.index()
    assert caught.value.reason == "unsigned_answer"


async def test_a_page_signed_for_another_route_is_refused() -> None:
    answers = recorded_answers()
    moved = reader(answers, signed_path=lambda path: f"{PEER_PREFIX}{INDEX}")
    with pytest.raises(Refused) as caught:
        await moved.craft(entry(answers))
    assert caught.value.reason == "unsigned_answer"


async def test_a_page_signed_with_another_token_is_refused() -> None:
    with pytest.raises(Refused):
        await reader(recorded_answers(), token="z" * 40).index()


def lose_the_second_page(answers: Answers) -> None:
    del answers[(AJRAKH_QUOTES, "c2")]
    answers[(AJRAKH_QUOTES, None)]["nextCursor"] = None


@pytest.mark.parametrize(
    "change",
    [
        lose_the_second_page,
        lambda a: a[(AJRAKH_QUOTES, "c2")]["recordings"][0].update(revision="changed"),
        lambda a: a[(AJRAKH_PHOTOGRAPHS, None)].update(photographs=[]),
    ],
)
async def test_a_craft_that_changed_while_it_was_read_is_refused(change: Any) -> None:
    answers = recorded_answers()
    change(answers)
    with pytest.raises(Refused) as caught:
        await reader(answers).craft(entry(answers))
    assert caught.value.reason == "snapshot_changed"


async def test_the_same_recording_on_two_pages_is_refused() -> None:
    answers = recorded_answers()
    answers[(AJRAKH_QUOTES, "c2")] = edited(
        answers[(AJRAKH_QUOTES, None)], lambda p: p.update(cursor="c2", nextCursor=None)
    )
    with pytest.raises(InvalidInput, match="rec-1' appears twice"):
        await reader(answers).craft(entry(answers))


async def test_pages_that_loop_are_refused() -> None:
    answers = recorded_answers()
    answers[(AJRAKH_QUOTES, "c2")]["nextCursor"] = "c2"
    with pytest.raises(InvalidInput, match="loop back"):
        await reader(answers).craft(entry(answers))


async def test_pages_past_the_limit_are_refused() -> None:
    answers = recorded_answers()
    peer = peer_for(enabled_settings(), "FIELD_REPOSITORY", transport=portal_transport(answers))
    limited = FieldVoicesReader(peer, image_hosts=frozenset({IMAGE_HOST}), max_pages=1)
    with pytest.raises(InvalidInput, match="past 1 pages"):
        await limited.craft(entry(answers))


async def test_personal_data_in_a_quote_drops_that_quote_and_its_lone_speaker() -> None:
    answers = recorded_answers()
    answers[(AJRAKH_QUOTES, "c2")]["recordings"][0]["quotes"][0]["english"] = "Call me on 98250 12345 7."
    voices = await reader(answers).craft(entry(answers))
    assert [r.id for r in voices.recordings] == ["rec-1"]
    assert [(d.kind, d.item_id, d.reasons) for d in voices.dropped] == [
        ("quote", "turn-3.2", ("phone-like number",))
    ]


async def test_personal_data_in_one_quote_keeps_the_rest_of_the_recording() -> None:
    answers = recorded_answers()
    answers[(AJRAKH_QUOTES, None)]["recordings"][0]["quotes"][1]["text"] = "mail asha@example.com"
    voices = await reader(answers).craft(entry(answers))
    first = voices.recordings[0]
    assert [q.id for q in first.quotes] == ["turn-11"]
    assert [a.id for a in first.artisans] == ["art-1"]
    assert [d.item_id for d in voices.dropped] == ["turn-14"]


async def test_personal_data_in_a_caption_drops_the_photograph() -> None:
    answers = recorded_answers()
    answers[(AJRAKH_PHOTOGRAPHS, None)]["photographs"][0]["caption"] = "Ask 2345 6789 0123 for prints"
    voices = await reader(answers).craft(entry(answers))
    assert voices.photographs == ()
    assert [(d.kind, d.item_id) for d in voices.dropped] == [("photograph", "photo-1")]


async def test_a_switched_off_portal_route_is_a_named_failure() -> None:
    with pytest.raises(ExternalFailure) as caught:
        await reader({}).index()
    assert (caught.value.kind, caught.value.status, caught.value.service) == (
        "not_found",
        404,
        "FIELD_REPOSITORY",
    )
    assert "field voices index answered 404" in str(caught.value)
    assert TOKEN not in str(caught.value)


def listed(answers: Answers, lines: str, *, recordings: int, quotes: int, photographs: int) -> None:
    ajrakh_entry(answers).update(
        recordings=recordings,
        quotes=quotes,
        photographs=photographs,
        digest=hashlib.sha256(lines.encode("utf-8")).hexdigest(),
    )


async def test_a_list_the_index_says_is_empty_is_not_asked_for() -> None:
    answers = recorded_answers()
    del answers[(AJRAKH_PHOTOGRAPHS, None)]
    lines = "R rec-1 91bdd4e889f5d9736c6c2fbd944dfd73\nR rec-2 f934cb90d32e02ebeebf08105f111c34\n"
    listed(answers, lines, recordings=2, quotes=3, photographs=0)
    seen: list[httpx.Request] = []
    voices = await reader(answers, seen=seen).craft(entry(answers))
    assert [r.url.params.get("cursor") for r in seen] == [None, "c2"]
    assert all(r.url.path.endswith("/quotes") for r in seen)
    assert ([r.id for r in voices.recordings], voices.photographs) == (["rec-1", "rec-2"], ())


async def test_recordings_that_go_back_in_time_across_pages_are_refused() -> None:
    answers = recorded_answers()
    answers[(AJRAKH_QUOTES, "c2")]["recordings"][0]["recordedAt"] = "2025-12-02T15:10:00+05:30"
    with pytest.raises(
        InvalidInput, match="recordings are out of the contract's order: rec-2 comes after rec-1"
    ):
        await reader(answers).craft(entry(answers))


async def test_an_untimed_photograph_comes_after_the_timed_ones() -> None:
    answers = recorded_answers()
    page = answers[(AJRAKH_PHOTOGRAPHS, None)]
    untimed = {**page["photographs"][0], "id": "photo-0", "takenAt": None}
    page["photographs"].insert(0, untimed)
    lines = (
        "P photo-0 7b44d54b1fb4b16a9fd145c5fc893613\n"
        "P photo-1 7b44d54b1fb4b16a9fd145c5fc893613\n"
        "R rec-1 91bdd4e889f5d9736c6c2fbd944dfd73\n"
        "R rec-2 f934cb90d32e02ebeebf08105f111c34\n"
    )
    listed(answers, lines, recordings=2, quotes=3, photographs=2)
    with pytest.raises(InvalidInput, match="photo-1 comes after photo-0"):
        await reader(answers).craft(entry(answers))
    page["photographs"].reverse()
    voices = await reader(answers).craft(entry(answers))
    assert [p.id for p in voices.photographs] == ["photo-1", "photo-0"]


async def test_a_workshop_title_is_never_kept_beside_an_unnamed_credit() -> None:
    answers = recorded_answers()
    workshop = answers[(AJRAKH_QUOTES, None)]["recordings"][0]["workshop"]
    answers[(AJRAKH_QUOTES, "c2")]["recordings"][0]["workshop"] = dict(workshop)
    unnamed = dict(answers[(AJRAKH_QUOTES, "c2")]["recordings"][0]["artisans"][0])
    answers[(AJRAKH_PHOTOGRAPHS, None)]["photographs"][0]["artisans"].append(unnamed)
    voices = await reader(answers).craft(entry(answers))
    named, untitled = voices.recordings
    assert named.workshop is not None and named.workshop.title == "Ajrakh documentation visit, Kachchh"
    assert untitled.workshop is not None and (untitled.workshop.title, untitled.workshop.district) == (
        None,
        "Kachchh",
    )
    photograph = voices.photographs[0]
    assert photograph.workshop is not None and photograph.workshop.title is None
    assert voices.dropped == ()


async def test_a_rate_limited_page_carries_the_wait_the_portal_asked_for() -> None:
    transport = httpx.MockTransport(lambda request: httpx.Response(429, headers={"Retry-After": "30"}))
    limited = field_voices_reader(enabled_settings(), transport=transport)
    with pytest.raises(ExternalFailure) as caught:
        await limited.index()
    failure = caught.value
    assert (failure.kind, failure.retryable, failure.retry_after) == ("rate_limit", True, 30.0)
