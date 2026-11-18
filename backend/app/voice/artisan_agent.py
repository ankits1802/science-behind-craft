from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

from app.research.evidence import personal_data_in
from app.research.untrusted import clean_untrusted_text
from app.schemas.artisan import TranscriptTurn
from app.schemas.voice import MAX_TURNS
from app.schemas.voice_llm import LlmChatRequest

from .agent_turn import CONVERSATION_ID_MAX_CHARS, AgentCall
from .artisan_guide import closing
from .artisan_records import ARTISAN_PURPOSE, ConversationRecord, TurnWrite
from .artisan_reply import ArtisanTools, KalaVigyanTurn, kalavigyan_turn, transcript_turn
from .artisan_session import ArtisanRefused, ConversationDeps, end_conversation
from .artisan_transcript import open_transcript, sealed_merge
from .binding import ARTISAN_NONCE_CONTEXT, bearer_matches, session_is_bound
from .llm import AgentReply, EndCall
from .privacy import heard_text
from .records import SessionRecord

__all__ = ["HeardMessage", "artisan_agent_reply", "authorised_artisan_session", "heard_message"]

MS = 1000


@dataclass(frozen=True)
class HeardMessage:
    text: str
    scrubbed: bool


async def authorised_artisan_session(
    deps: ConversationDeps, call: AgentCall, *, now: datetime
) -> tuple[SessionRecord, ConversationRecord]:
    conversation_id = (call.conversation_id or "").strip()
    voice = deps.voice
    if not bearer_matches(call.authorization, voice.llm_bearer) or voice.hmac_key is None:
        raise ArtisanRefused("not_found")
    if not conversation_id or len(conversation_id) > CONVERSATION_ID_MAX_CHARS:
        raise ArtisanRefused("not_found")
    record = await deps.store.by_conversation(conversation_id)
    if (
        record is None
        or record.purpose != ARTISAN_PURPOSE
        or record.transport != "AGENT"
        or not record.live_at(now)
        or record.turn_count > MAX_TURNS
        or not session_is_bound(voice.hmac_key, record, conversation_id, context=ARTISAN_NONCE_CONTEXT)
    ):
        raise ArtisanRefused("not_found")
    conversation = await deps.artisans.by_voice_session(record.id)
    if conversation is None or conversation.ended_at is not None:
        raise ArtisanRefused("not_found")
    return record, conversation


def heard_message(request: LlmChatRequest) -> HeardMessage:
    asked = next((m for m in reversed(request.messages) if m.role == "user"), None)
    raw = clean_untrusted_text(asked.content or "") if asked else ""
    return HeardMessage(text=heard_text(raw), scrubbed=bool(personal_data_in(raw)))


async def artisan_agent_reply(
    session: SessionRecord,
    conversation: ConversationRecord,
    heard: HeardMessage,
    *,
    deps: ConversationDeps,
    tools: ArtisanTools,
    on_end: Callable[[ConversationRecord], None],
) -> AgentReply:
    if not heard.text:
        return AgentReply()
    now = deps.clock()
    begun = await deps.store.begin_turn(session.id, now)
    if begun is None:
        return await _closed(conversation, deps, on_end, now)
    await _kept_heard(conversation, begun, heard, deps, now)
    fresh = await deps.artisans.by_id(conversation.id) or conversation
    transcript = open_transcript(deps.cipher, fresh.transcript)
    reply = await kalavigyan_turn(
        fresh, begun, transcript, tools=tools, ids=(deps.ids(), deps.ids()), now=now
    )
    await _kept_reply(fresh, begun, reply, deps, now)
    if reply.closing:
        await _ended(fresh, deps, on_end, now)
        return AgentReply(end_call=EndCall(reason="done", message=reply.text))
    return AgentReply(parts=(reply.text,))


async def _kept_heard(
    conversation: ConversationRecord,
    session: SessionRecord,
    heard: HeardMessage,
    deps: ConversationDeps,
    now: datetime,
) -> None:
    transcript = open_transcript(deps.cipher, conversation.transcript)
    previous_end = transcript.turns[-1].end_ms if transcript.turns else 0
    arrived = max(previous_end, round((now - session.started_at).total_seconds() * MS))
    turn = TranscriptTurn(
        id=deps.ids(),
        ordinal=len(transcript.turns),
        speaker="ARTISAN",
        text=heard.text,
        start_ms=previous_end,
        end_ms=arrived,
        scrubbed=heard.scrubbed,
    )
    await deps.artisans.save_turn(conversation.id, TurnWrite(merge=sealed_merge(deps.cipher, turn)))


async def _kept_reply(
    conversation: ConversationRecord,
    session: SessionRecord,
    reply: KalaVigyanTurn,
    deps: ConversationDeps,
    now: datetime,
) -> None:
    start = round((now - session.started_at).total_seconds() * MS)
    turn = transcript_turn(reply, start_ms=start, end_ms=start)
    topics = tuple(dict.fromkeys([*conversation.topics_asked, *([turn.topic] if turn.topic else [])]))
    answer = reply.answer.answer(0) if reply.answer else None
    write = TurnWrite(merge=sealed_merge(deps.cipher, turn), topics_asked=topics, answer=answer)
    await deps.artisans.save_turn(conversation.id, write)


async def _ended(
    conversation: ConversationRecord,
    deps: ConversationDeps,
    on_end: Callable[[ConversationRecord], None],
    now: datetime,
) -> None:
    _, finished = await end_conversation(conversation, deps, now=now)
    on_end(finished)


async def _closed(
    conversation: ConversationRecord,
    deps: ConversationDeps,
    on_end: Callable[[ConversationRecord], None],
    now: datetime,
) -> AgentReply:
    await _ended(conversation, deps, on_end, now)
    return AgentReply(end_call=EndCall(reason="turns", message=closing(conversation.language)))
