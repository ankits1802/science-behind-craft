from __future__ import annotations

import logging
from collections import Counter
from collections.abc import Mapping
from dataclasses import replace

from app.core.errors import ExternalFailure
from app.research.composition import (
    COMPOSE_RETRIES,
    ComposeCandidate,
    ComposedAnswer,
    ComposedSection,
    ComposedSentence,
    ComposeRequest,
    sentence_level,
)
from app.research.planning import OPEN_QUESTION_LEVEL
from app.research.structured import StructuredModel, reply_object

from .drafts import DraftAnswer, DraftSection, DraftSentence, parsed_answer, parsed_replacements
from .prompt import (
    COMPOSE_SYSTEM_PROMPT,
    REGENERATE_SYSTEM_PROMPT,
    compose_message,
    compose_schema,
    regenerate_message,
    regenerate_schema,
)

__all__ = ["ModelComposer", "assembled_answer"]

logger = logging.getLogger(__name__)


class ModelComposer:
    def __init__(self, *, model: StructuredModel) -> None:
        self._model = model

    async def compose(self, request: ComposeRequest) -> ComposedAnswer:
        if not request.candidates:
            return ComposedAnswer(not_enough_evidence=request.searched)
        draft, retries_left = await self._first_draft(request)
        failed = draft.failed
        if failed and retries_left:
            draft = await self._regenerated(request, draft, failed)
        _log_dropped(draft)
        return assembled_answer(draft, request)

    async def _first_draft(self, request: ComposeRequest) -> tuple[DraftAnswer, int]:
        user = compose_message(request)
        schema = compose_schema()
        for attempt in range(COMPOSE_RETRIES):
            reply = await self._model(system=COMPOSE_SYSTEM_PROMPT, user=user, schema=schema)
            try:
                return parsed_answer(reply_object(reply), request.allowed), COMPOSE_RETRIES - attempt
            except ExternalFailure as error:
                logger.warning("compose reply %d unusable: %s", attempt + 1, error)
        reply = await self._model(system=COMPOSE_SYSTEM_PROMPT, user=user, schema=schema)
        return parsed_answer(reply_object(reply), request.allowed), 0

    async def _regenerated(
        self, request: ComposeRequest, draft: DraftAnswer, failed: list[DraftSentence]
    ) -> DraftAnswer:
        reply = await self._model(
            system=REGENERATE_SYSTEM_PROMPT,
            user=regenerate_message(request, failed),
            schema=regenerate_schema(len(failed)),
        )
        try:
            replacements = parsed_replacements(reply_object(reply), len(failed), request.allowed)
        except ExternalFailure as error:
            logger.warning("regenerate reply unusable, failing sentences dropped: %s", error)
            return draft
        return _with_replacements(draft, replacements)


def assembled_answer(draft: DraftAnswer, request: ComposeRequest) -> ComposedAnswer:
    allowed = request.allowed
    sections: list[ComposedSection] = []
    open_questions: list[ComposedSentence] = []
    for section in draft.sections:
        kept = [s.sentence for s in section.sentences if s.passes and s.sentence is not None]
        stated = [s for s in kept if not _is_open_question(s, allowed)]
        open_questions += [s for s in kept if _is_open_question(s, allowed)]
        if stated:
            sections.append(ComposedSection(heading=section.heading, sentences=stated))
    if not sections and not open_questions:
        return ComposedAnswer(not_enough_evidence=request.searched)
    return ComposedAnswer(sections=sections, open_questions=open_questions, follow_ups=list(draft.follow_ups))


def _with_replacements(draft: DraftAnswer, replacements: Mapping[int, DraftSentence]) -> DraftAnswer:
    slot = 0
    sections: list[DraftSection] = []
    for section in draft.sections:
        sentences: list[DraftSentence] = []
        for sentence in section.sentences:
            if sentence.passes:
                sentences.append(sentence)
                continue
            if slot in replacements:
                sentences.append(replace(replacements[slot], heading=section.heading))
            slot += 1
        sections.append(DraftSection(section.heading, tuple(sentences)))
    return DraftAnswer(sections=tuple(sections), follow_ups=draft.follow_ups)


def _is_open_question(sentence: ComposedSentence, allowed: Mapping[str, ComposeCandidate]) -> bool:
    return sentence_level(sentence, allowed) == OPEN_QUESTION_LEVEL


def _log_dropped(draft: DraftAnswer) -> None:
    failed = draft.failed
    if failed:
        kinds = Counter(kind for sentence in failed for kind in sentence.problem_kinds)
        logger.warning("compose dropped %d sentence(s): %s", len(failed), dict(sorted(kinds.items())))
