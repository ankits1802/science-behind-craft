from __future__ import annotations

import uuid
from dataclasses import dataclass, replace
from datetime import datetime

from app.research.structured import StructuredModel
from app.research.vocabulary import CANONICAL_LANGUAGE
from app.schemas.artisan import ArtisanTranscript, TranscriptTurn
from app.schemas.voice import MAX_TURNS

from .artisan_guide import TOPIC_CONCEPT_TYPES, TOPIC_NAMES, closing
from .artisan_records import ConversationRecord
from .artisan_turn import InterviewAsk, Question, planned_question, spoken_question
from .pack import VoicePack
from .records import SessionRecord
from .turns import SpokenTurn, TurnAsk, TurnTools, spoken_turn

__all__ = [
    "GAP_CLAIMS_MIN",
    "ArtisanTools",
    "KalaVigyanTurn",
    "kalavigyan_turn",
    "knowledge_gaps",
    "transcript_turn",
]

GAP_CLAIMS_MIN = 3
VERIFIED = "VERIFIED"


@dataclass(frozen=True)
class ArtisanTools:
    interview: StructuredModel
    turns: TurnTools


@dataclass(frozen=True, kw_only=True)
class KalaVigyanTurn:
    turn_id: uuid.UUID
    question: Question
    answer: SpokenTurn | None
    text: str
    english: str
    closing: bool


def knowledge_gaps(pack: VoicePack) -> tuple[str, ...]:
    held: dict[str, int] = {}
    for view in pack.cited.views.values():
        for topic, kinds in TOPIC_CONCEPT_TYPES.items():
            if view.concept_type in kinds:
                held[topic] = held.get(topic, 0) + 1
    return tuple(TOPIC_NAMES[topic] for topic in TOPIC_NAMES if held.get(topic, 0) < GAP_CLAIMS_MIN)


async def kalavigyan_turn(
    conversation: ConversationRecord,
    session: SessionRecord,
    transcript: ArtisanTranscript,
    *,
    tools: ArtisanTools,
    ids: tuple[uuid.UUID, uuid.UUID],
    now: datetime,
) -> KalaVigyanTurn:
    turn_id, answer_id = ids
    pack = await tools.turns.pack(conversation.craft, VERIFIED)
    ask = InterviewAsk(
        craft=conversation.craft,
        language=conversation.language,
        transcript=transcript,
        asked_before=conversation.topics_asked,
        gaps=knowledge_gaps(pack),
        seconds_left=max(0, int((session.hard_end - now).total_seconds())),
        turns_left=max(0, _turns_left(session)),
    )
    question = await planned_question(ask, tools.interview)
    if question.close:
        return _closing(turn_id, conversation.language, question)
    answer = (
        await _answer(session, transcript, tools.turns, ids=(turn_id, answer_id), now=now)
        if question.asked
        else None
    )
    question = await spoken_question(question, ask, tools.turns.translation)
    if question.close or question.spoken is None or question.english is None:
        return _closing(turn_id, conversation.language, question)
    text = f"{answer.spoken.strip()} {question.spoken}" if answer else question.spoken
    return KalaVigyanTurn(
        turn_id=turn_id, question=question, answer=answer, text=text, english=question.english, closing=False
    )


def transcript_turn(turn: KalaVigyanTurn, *, start_ms: int, end_ms: int) -> TranscriptTurn:
    return TranscriptTurn(
        id=turn.turn_id,
        ordinal=0,
        speaker="KALAVIGYAN",
        text=turn.text,
        english=turn.english,
        topic=turn.question.topic if not turn.closing else None,
        answer_id=turn.answer.answer_id if turn.answer else None,
        start_ms=start_ms,
        end_ms=max(start_ms, end_ms),
    )


async def _answer(
    session: SessionRecord,
    transcript: ArtisanTranscript,
    tools: TurnTools,
    *,
    ids: tuple[uuid.UUID, uuid.UUID],
    now: datetime,
) -> SpokenTurn | None:
    turn_id, answer_id = ids
    heard = [turn.text for turn in transcript.turns if turn.speaker == "ARTISAN"]
    if not heard:
        return None
    verified = replace(session, mode=VERIFIED)
    return await spoken_turn(
        TurnAsk.begun(verified, heard[-1], turn_id=turn_id, answer_id=answer_id, now=now), tools
    )


def _closing(turn_id: uuid.UUID, language: str, question: Question) -> KalaVigyanTurn:
    return KalaVigyanTurn(
        turn_id=turn_id,
        question=replace(question, close=True, topic=None),
        answer=None,
        text=closing(language),
        english=closing(CANONICAL_LANGUAGE),
        closing=True,
    )


def _turns_left(session: SessionRecord) -> int:
    return MAX_TURNS - session.turn_count
