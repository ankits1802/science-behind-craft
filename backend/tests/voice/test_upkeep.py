import uuid
from dataclasses import replace
from datetime import timedelta
from pathlib import Path

import httpx

from app.providers.elevenlabs import ElevenLabs
from app.voice.upkeep import run_upkeep

from .fakes import START, MemoryStore, agent_session, cipher, session

FIXTURES = Path(__file__).parent / "fixtures"
NOW = START + timedelta(days=31)


def elevenlabs(status_file: str | None, *, status: int = 200) -> tuple[ElevenLabs, list[str]]:
    calls: list[str] = []

    def answer(request: httpx.Request) -> httpx.Response:
        calls.append(f"{request.method} {request.url.path}")
        if request.method == "DELETE":
            return httpx.Response(200, json={})
        if status_file is None:
            return httpx.Response(status, json={"detail": "not found"})
        return httpx.Response(status, content=(FIXTURES / status_file).read_bytes())

    return ElevenLabs(
        api_key="test-only-elevenlabs-key", client=httpx.AsyncClient(transport=httpx.MockTransport(answer))
    ), calls


def ended_agent_session(reserved: int = 252) -> MemoryStore:
    store = MemoryStore()
    record = agent_session(reserved_seconds=reserved, ended_at=START + timedelta(minutes=4))
    store.sessions[record.id] = record
    return store


async def test_transcripts_are_purged_after_thirty_days() -> None:
    store = MemoryStore()
    kept = session(
        id=uuid.uuid4(), ended_at=START, retention_until=NOW + timedelta(days=1), transcript=cipher().seal({})
    )
    old = session(
        id=uuid.uuid4(),
        ended_at=START,
        retention_until=NOW - timedelta(seconds=1),
        transcript=cipher().seal({}),
    )
    store.sessions |= {kept.id: kept, old.id: old}
    report = await run_upkeep(store, None, now=NOW)
    assert report.purged == 1
    assert store.sessions[old.id].transcript is None and store.sessions[kept.id].transcript is not None


async def test_a_session_left_open_is_closed_at_its_hard_end() -> None:
    store = MemoryStore()
    left = session()
    store.sessions[left.id] = left
    report = await run_upkeep(store, None, now=NOW)
    assert report.closed == 1 and store.sessions[left.id].ended_at == left.hard_end


async def test_a_finished_call_is_billed_its_duration_and_refunded_the_rest() -> None:
    store = ended_agent_session()
    voice, calls = elevenlabs("conversation_done.json")
    report = await run_upkeep(store, voice, now=NOW)
    [record] = store.sessions.values()
    assert record.billed_seconds == 212
    refund = store.ledger[f"voice-refund:{record.id}"]
    assert (refund.units, refund.resource) == (-40, "VOICE_SECONDS")
    assert (report.reconciled, report.refunded_seconds, report.deleted) == (1, 40, 1)
    assert calls[-1] == "DELETE /v1/convai/conversations/conv_0123456789abcdef"


async def test_a_call_that_ran_past_its_hold_is_charged_the_rest() -> None:
    store = ended_agent_session(reserved=200)
    report = await run_upkeep(store, elevenlabs("conversation_done.json")[0], now=NOW)
    [record] = store.sessions.values()
    assert record.billed_seconds == 212
    [charge] = store.ledger.values()
    assert (charge.key, charge.units) == (f"voice-settle:{record.id}", 12)
    assert (report.charged_seconds, report.refunded_seconds) == (12, 0)


async def test_a_call_billed_exactly_its_hold_writes_no_row() -> None:
    store = ended_agent_session(reserved=212)
    await run_upkeep(store, elevenlabs("conversation_done.json")[0], now=NOW)
    assert next(iter(store.sessions.values())).billed_seconds == 212 and store.ledger == {}


async def test_a_call_still_processing_waits_for_the_next_run() -> None:
    store = ended_agent_session()
    report = await run_upkeep(store, elevenlabs("conversation_processing.json")[0], now=NOW)
    assert report.waiting == 1 and next(iter(store.sessions.values())).billed_seconds is None


async def test_a_call_elevenlabs_no_longer_holds_keeps_what_was_reserved() -> None:
    store = ended_agent_session()
    await run_upkeep(store, elevenlabs(None, status=404)[0], now=NOW)
    assert next(iter(store.sessions.values())).billed_seconds == 252


async def test_a_failed_lookup_is_reported_and_retried_later() -> None:
    store = ended_agent_session()
    report = await run_upkeep(store, elevenlabs(None, status=503)[0], now=NOW)
    assert len(report.failures) == 1 and next(iter(store.sessions.values())).billed_seconds is None


async def test_relay_sessions_are_not_looked_up() -> None:
    store = MemoryStore()
    record = replace(session(), ended_at=START + timedelta(minutes=2))
    store.sessions[record.id] = record
    voice, calls = elevenlabs("conversation_done.json")
    report = await run_upkeep(store, voice, now=NOW)
    assert calls == [] and report.reconciled == 0


async def test_a_silent_call_without_a_single_turn_is_billed_what_elevenlabs_counted() -> None:
    store = ended_agent_session(reserved=540)
    assert next(iter(store.sessions.values())).turn_count == 0
    await run_upkeep(store, elevenlabs("conversation_done.json")[0], now=NOW)
    [record] = store.sessions.values()
    assert record.billed_seconds == 212
    assert store.ledger[f"voice-refund:{record.id}"].units == -(540 - 212)


async def test_a_call_left_connected_after_its_row_ended_is_charged_past_its_hold() -> None:
    store = ended_agent_session(reserved=30)
    await run_upkeep(store, elevenlabs("conversation_done.json")[0], now=NOW)
    [record] = store.sessions.values()
    assert store.ledger[f"voice-settle:{record.id}"].units == 212 - 30
