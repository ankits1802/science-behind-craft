import json
import uuid
from dataclasses import dataclass, replace
from datetime import UTC, datetime, timedelta
from pathlib import Path

import httpx
import pytest

from app.core.errors import ExternalFailure
from app.schemas.voice import AgentSessionStarted, RelaySessionStarted
from app.voice import sessions
from app.voice.availability import voice_availability
from app.voice.binding import session_is_bound
from app.voice.notice import VOICE_NOTICE_VERSION
from app.voice.records import SessionRecord
from app.voice.runtime import VoiceRuntime, VoiceSettings
from app.voice.seconds import START_WINDOW_SECONDS
from app.voice.sessions import StartAsk, VoiceRefused, end_session, start_session

from .fakes import (
    BEARER,
    CONVERSATION_ID,
    CRAFT,
    HMAC_KEY,
    USER_ID,
    MemoryStore,
    agent_session,
    cipher,
    session,
)

NOW = datetime(2026, 11, 16, 10, 30, tzinfo=UTC)
FIXTURES = Path(__file__).parent / "fixtures"


@dataclass
class Learner:
    id: uuid.UUID = USER_ID
    role: str = "STUDENT"
    emailVerifiedAt: datetime | None = NOW


def voice(transport: str = "RELAY", **changes: object) -> VoiceSettings:
    base = VoiceSettings(
        transport=transport,
        max_live_sessions=5,
        voice_id="voice_1",
        api_key="test-only-elevenlabs-key",
        agent_id="agent_test",
        llm_bearer=BEARER,
        hmac_key=HMAC_KEY,
        cipher=cipher(),
    )
    return replace(base, **changes)


def runtime(
    *, reachable: bool = True, token_status: int = 200, conversation: str = "conversation_done.json"
) -> tuple[VoiceRuntime, list[str]]:
    paths: list[str] = []

    def answer(request: httpx.Request) -> httpx.Response:
        paths.append(f"{request.method} {request.url.path}")
        if request.url.path == "/v1/user":
            return httpx.Response(200 if reachable else 401, json={})
        if request.url.path.startswith("/v1/convai/conversations/"):
            if request.method == "DELETE":
                return httpx.Response(200, json={})
            return httpx.Response(200, content=(FIXTURES / conversation).read_bytes())
        return httpx.Response(token_status, content=(FIXTURES / "conversation_token.json").read_bytes())

    return VoiceRuntime(client=httpx.AsyncClient(transport=httpx.MockTransport(answer))), paths


def consenting_store(**changes: object) -> MemoryStore:
    store = MemoryStore(**changes)
    store.consents.add((USER_ID, VOICE_NOTICE_VERSION))
    return store


async def start(
    store: MemoryStore,
    *,
    learner: Learner | None = None,
    settings: VoiceSettings | None = None,
    **ask: object,
) -> dict[str, object]:
    chosen = {"craft_slug": CRAFT.slug, "mode": "HYBRID", "language": "en", **ask}
    request = StartAsk(user=learner or Learner(), **chosen)
    return await start_session(request, store=store, runtime=runtime()[0], voice=settings or voice(), now=NOW)


async def refused(store: MemoryStore, **kwargs: object) -> VoiceRefused:
    with pytest.raises(VoiceRefused) as error:
        await start(store, **kwargs)
    return error.value


@pytest.mark.usefixtures("allowances_an_owner_might_set")
async def test_a_relay_session_starts_with_the_day_s_time_left() -> None:
    store = consenting_store(used_before=60)
    started = RelaySessionStarted.model_validate(await start(store))
    assert (started.max_duration_seconds, started.remaining_seconds, started.max_turns) == (540, 540, 40)
    assert started.expires_at == NOW + timedelta(seconds=START_WINDOW_SECONDS)
    assert (started.max_audio_bytes, started.audio_bits_per_second) == (300_000, 32_000)
    assert started.craft == CRAFT and started.audio_types == [
        "audio/webm",
        "audio/ogg",
        "audio/mp4",
        "audio/wav",
    ]
    [record] = store.sessions.values()
    assert record.transport == "RELAY" and record.user_id == USER_ID and record.chat_id is not None


async def test_by_default_a_session_starts_whatever_the_day_has_used_and_counts_no_time_left() -> None:
    store = consenting_store(used_before=100_000)
    started = RelaySessionStarted.model_validate(await start(store))
    assert (started.max_duration_seconds, started.remaining_seconds) == (sessions.MAX_SESSION_SECONDS, None)
    shown = await voice_availability(Learner(), store=store, runtime=runtime()[0], voice=voice(), now=NOW)
    assert shown["remainingSeconds"] is None


async def test_an_agent_session_binds_the_conversation_and_hands_out_only_the_token() -> None:
    store = consenting_store()
    payload = await start(store, settings=voice("AGENT"))
    started = AgentSessionStarted.model_validate(payload)
    assert started.conversation_token == "fixture-conversation-token-not-a-credential"
    text = json.dumps(payload)
    assert "conv_0123456789abcdef" not in text and "kvs1" not in text
    [record] = store.sessions.values()
    assert record.conversation_id == "conv_0123456789abcdef"
    assert session_is_bound(HMAC_KEY, record, "conv_0123456789abcdef")


@pytest.mark.usefixtures("allowances_an_owner_might_set")
async def test_an_agent_session_holds_its_whole_length_at_the_start() -> None:
    store = consenting_store(used_before=60)
    await start(store, settings=voice("AGENT"))
    [record] = store.sessions.values()
    hold = store.ledger[f"voice:{record.id}:hold"]
    assert (hold.units, record.max_duration_seconds, record.reserved_seconds) == (540, 540, 540)


def ended_agent_call(**changes: object) -> SessionRecord:
    fields: dict[str, object] = {
        "id": uuid.uuid4(),
        "started_at": NOW - timedelta(seconds=90),
        "expires_at": NOW + timedelta(seconds=30),
        "ended_at": NOW - timedelta(seconds=30),
        "nonce_hash": None,
        "reserved_seconds": 540,
    }
    return agent_session(**(fields | changes))


async def test_an_ended_call_still_open_at_elevenlabs_keeps_the_user_s_slot() -> None:
    store = consenting_store()
    call = ended_agent_call()
    store.sessions[call.id] = call
    request = StartAsk(user=Learner(), craft_slug=None, mode="HYBRID", language="en")
    still_running = runtime(conversation="conversation_processing.json")[0]
    with pytest.raises(VoiceRefused) as error:
        await start_session(request, store=store, runtime=still_running, voice=voice("AGENT"), now=NOW)
    assert error.value.reason == "live_session"
    assert store.sessions[call.id].billed_seconds is None and store.ledger == {}


@pytest.mark.usefixtures("allowances_an_owner_might_set")
async def test_a_finished_call_is_settled_at_the_next_start_and_frees_its_hold() -> None:
    store = consenting_store()
    call = ended_agent_call()
    store.sessions[call.id] = call
    store.used_before = 540
    request = StartAsk(user=Learner(), craft_slug=None, mode="HYBRID", language="en")
    started_on, paths = runtime()
    payload = await start_session(request, store=store, runtime=started_on, voice=voice("AGENT"), now=NOW)
    assert store.sessions[call.id].billed_seconds == 212
    assert store.ledger[f"voice-refund:{call.id}"].units == -(540 - 212)
    assert payload["remainingSeconds"] == 600 - 212
    assert f"DELETE /v1/convai/conversations/{CONVERSATION_ID}" in paths


@pytest.mark.usefixtures("allowances_an_owner_might_set")
async def test_availability_settles_a_finished_call_before_showing_the_time_left() -> None:
    store = MemoryStore(used_before=540)
    call = ended_agent_call()
    store.sessions[call.id] = call
    shown = await voice_availability(
        Learner(), store=store, runtime=runtime()[0], voice=voice("AGENT"), now=NOW
    )
    assert shown["remainingSeconds"] == 600 - 212
    assert store.sessions[call.id].billed_seconds == 212


async def test_a_settled_call_or_one_past_its_window_no_longer_blocks() -> None:
    store = consenting_store()
    settled = ended_agent_call(billed_seconds=120)
    lapsed = ended_agent_call(
        started_at=NOW - timedelta(seconds=720), expires_at=NOW - timedelta(seconds=600)
    )
    store.sessions |= {settled.id: settled, lapsed.id: lapsed}
    assert not await store.has_live(USER_ID, NOW)


async def test_a_failed_token_ends_the_new_session() -> None:
    store = consenting_store()
    request = StartAsk(user=Learner(), craft_slug=None, mode="HYBRID", language="en")
    with pytest.raises(ExternalFailure, match="ElevenLabs answered 503"):
        await start_session(
            request, store=store, runtime=runtime(token_status=503)[0], voice=voice("AGENT"), now=NOW
        )
    [record] = store.sessions.values()
    assert record.ended_at == NOW


async def test_the_checks_run_in_the_contract_order(monkeypatch: pytest.MonkeyPatch) -> None:
    assert (await refused(MemoryStore(), learner=Learner(role="VISITOR"))).reason == "capability"
    assert (await refused(MemoryStore(), learner=Learner(emailVerifiedAt=None))).reason == "unverified_email"
    assert (await refused(MemoryStore())).reason == "consent"
    monkeypatch.setattr(sessions, "VOICE_LANGUAGES", ("en", "ta"))
    assert (await refused(consenting_store(), language="hi")).reason == "language"
    assert (await refused(consenting_store(), craft_slug="no-such-craft")).reason == "craft"
    assert (await refused(consenting_store(), settings=voice(api_key=None))).reason == "not_configured"
    assert (
        await refused(consenting_store(), settings=voice("AGENT", agent_id=None))
    ).reason == "not_configured"


async def test_one_live_session_per_user() -> None:
    store = consenting_store()
    store.sessions[uuid.uuid4()] = session(started_at=NOW, expires_at=NOW + timedelta(seconds=60))
    assert (await refused(store)).reason == "live_session"


async def test_a_lapsed_session_no_longer_blocks_a_new_one() -> None:
    store = consenting_store()
    old = session(started_at=NOW - timedelta(hours=1), expires_at=NOW - timedelta(minutes=58))
    store.sessions[old.id] = old
    await start(store)
    assert store.sessions[old.id].ended_at == old.hard_end


@pytest.mark.usefixtures("allowances_an_owner_might_set")
async def test_less_than_thirty_seconds_left_waits_for_midnight_india_time() -> None:
    error = await refused(consenting_store(used_before=600 - 29))
    midnight_ist = datetime(2026, 11, 16, 18, 30, tzinfo=UTC)
    assert error.reason == "quota" and error.retry_after == int((midnight_ist - NOW).total_seconds())


async def test_the_platform_wide_limit_asks_to_retry_in_thirty_seconds() -> None:
    error = await refused(consenting_store(), settings=voice(max_live_sessions=0))
    assert (error.reason, error.retry_after) == ("busy", 30)


async def test_unreachable_elevenlabs_is_not_configured() -> None:
    store = consenting_store()
    request = StartAsk(user=Learner(), craft_slug=None, mode="HYBRID", language="en")
    with pytest.raises(VoiceRefused) as error:
        await start_session(request, store=store, runtime=runtime(reachable=False)[0], voice=voice(), now=NOW)
    assert error.value.reason == "not_configured"


async def test_ending_twice_answers_the_same() -> None:
    store = consenting_store()
    started = await start(store)
    session_id = uuid.UUID(str(started["voiceSessionId"]))
    first = await end_session(store, Learner(), session_id, now=NOW + timedelta(seconds=90))
    second = await end_session(store, Learner(), session_id, now=NOW + timedelta(seconds=200))
    assert first == second and first["endedAt"] == "2026-11-16T10:31:30Z"
    with pytest.raises(VoiceRefused):
        await end_session(store, Learner(id=uuid.uuid4()), session_id, now=NOW)


@pytest.mark.usefixtures("allowances_an_owner_might_set")
async def test_availability_names_the_transport_consent_and_time_left() -> None:
    store = MemoryStore(used_before=60)
    shown = await voice_availability(Learner(), store=store, runtime=runtime()[0], voice=voice(), now=NOW)
    assert shown["configured"] is True and shown["transport"] == "RELAY"
    assert shown["consentRequired"] is True and shown["remainingSeconds"] == 540
    assert shown["noticeVersion"] == VOICE_NOTICE_VERSION
    codes = ["en", "hi", "bn", "ta", "te", "mr", "gu", "kn", "ml", "or", "pa", "as", "ur"]
    assert [option["code"] for option in shown["languages"]] == codes
    assert shown["languages"][-1] == {
        "code": "ur",
        "label": "Urdu",
        "autonym": "اردو",
        "script": "Arab",
        "direction": "rtl",
    }


async def test_a_session_starts_in_any_offered_language() -> None:
    store = consenting_store()
    started = RelaySessionStarted.model_validate(await start(store, language="ur"))
    [record] = store.sessions.values()
    assert started.language == "ur" and record.language == "ur"


async def test_availability_hides_voice_that_cannot_work() -> None:
    store = MemoryStore()
    hidden = {
        "configured": False,
        "transport": None,
        "languages": [],
        "noticeVersion": None,
        "consentRequired": False,
        "remainingSeconds": None,
    }
    unverified = Learner(emailVerifiedAt=None)
    assert (
        await voice_availability(unverified, store=store, runtime=runtime()[0], voice=voice(), now=NOW)
        == hidden
    )
    missing = voice(cipher=None)
    assert (
        await voice_availability(Learner(), store=store, runtime=runtime()[0], voice=missing, now=NOW)
        == hidden
    )
    down = runtime(reachable=False)[0]
    assert await voice_availability(Learner(), store=store, runtime=down, voice=voice(), now=NOW) == hidden
