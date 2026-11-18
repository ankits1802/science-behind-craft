from __future__ import annotations

import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

from app.schemas.voice import MAX_SESSION_SECONDS, MAX_TURNS
from app.schemas.voice_llm import LlmChatRequest

from .binding import bearer_matches, session_is_bound
from .llm import AgentReply, EndCall
from .phrases import END_CALL_REPLIES, phrase
from .privacy import TranscriptCipher, heard_text
from .records import SessionRecord, TurnSave, VoiceStore
from .runtime import VoiceSettings
from .sessions import VoiceRefused
from .transcript import turn_merge
from .turns import TurnAsk, TurnTools, spoken_turn

__all__ = ["CONVERSATION_ID_MAX_CHARS", "AgentCall", "agent_reply", "authorised_session", "last_question"]

CONVERSATION_ID_MAX_CHARS = 120
ASK_PURPOSE = "ASK"
Clock = Callable[[], datetime]


@dataclass(frozen=True)
class AgentCall:
    authorization: str | None
    conversation_id: str | None


async def authorised_session(
    store: VoiceStore, voice: VoiceSettings, call: AgentCall, *, now: datetime
) -> SessionRecord:
    conversation_id = (call.conversation_id or "").strip()
    if not bearer_matches(call.authorization, voice.llm_bearer) or voice.hmac_key is None:
        raise VoiceRefused("unauthorized", message="unauthorized")
    if not conversation_id or len(conversation_id) > CONVERSATION_ID_MAX_CHARS:
        raise VoiceRefused("unauthorized", message="unauthorized")
    record = await store.by_conversation(conversation_id)
    if (
        record is None
        or record.purpose != ASK_PURPOSE
        or record.transport != "AGENT"
        or not record.live_at(now)
        or record.turn_count > MAX_TURNS
    ):
        raise VoiceRefused("unauthorized", message="unauthorized")
    if not session_is_bound(voice.hmac_key, record, conversation_id):
        raise VoiceRefused("unauthorized", message="unauthorized")
    return record


def last_question(request: LlmChatRequest) -> str:
    asked = next(m for m in reversed(request.messages) if m.role == "user")
    return heard_text(asked.content or "")


async def agent_reply(
    record: SessionRecord,
    question: str,
    *,
    store: VoiceStore,
    tools: TurnTools,
    cipher: TranscriptCipher,
    clock: Clock,
    ids: Callable[[], uuid.UUID] = uuid.uuid4,
) -> AgentReply:
    if not question:
        return AgentReply()
    now = clock()
    ending = _ending(record, now)
    if ending is not None:
        await store.end(record.id, now)
        return AgentReply(end_call=ending)
    begun = await store.begin_turn(record.id, now)
    if begun is None:
        return AgentReply(end_call=_end_call("turns", record.language))
    started = time.perf_counter()
    turn = await spoken_turn(TurnAsk.begun(begun, question, turn_id=ids(), answer_id=ids(), now=now), tools)
    merge, _ = turn_merge(cipher, turn)
    latency = round((time.perf_counter() - started) * 1000)
    await store.save_turn(record.id, TurnSave(merge=merge, answer=turn.answer(latency)))
    return AgentReply(parts=turn.parts)


def _ending(record: SessionRecord, now: datetime) -> EndCall | None:
    if (now - record.started_at).total_seconds() >= record.max_duration_seconds:
        cut_by_quota = record.max_duration_seconds < MAX_SESSION_SECONDS
        return _end_call("quota" if cut_by_quota else "turns", record.language)
    if record.turn_count >= MAX_TURNS:
        return _end_call("turns", record.language)
    return None


def _end_call(reason: str, language: str) -> EndCall:
    return EndCall(reason=reason, message=phrase(END_CALL_REPLIES[reason], language))
