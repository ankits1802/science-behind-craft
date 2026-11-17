from __future__ import annotations

import uuid
from collections.abc import Mapping, Sequence
from types import MappingProxyType

from app.research.planning import OPEN_QUESTION_LEVEL
from app.research.sections import FALLBACK_DISCIPLINE, SectionSpec, block_id
from app.research.vocabulary import CANONICAL_LANGUAGE, LEVEL_ORDER

from .answer_events import STORED_ANSWER_LIMIT, STORED_OPEN_QUESTION_LIMIT, CitedClaims, stored_follow_ups
from .answer_translation import AnswerTranslation, translated_block, translated_sentences
from .explainer_events import ExplainerStream
from .knowledge_view import ClaimView, order_claims, section_heading
from .section_blocks import KeptSentence, cited_sentence, prose_block

__all__ = ["HEADING_DISCIPLINES", "stream_stored_answer"]

HEADING_DISCIPLINES: Mapping[str, str] = MappingProxyType(
    {
        "The tradition": "OVERVIEW",
        "History": "HISTORY",
        "Design": "DESIGN",
        "Materials and tools": "MATERIALS",
        "Process": "PROCESS",
        "The artisan's judgement": "PROCESS",
        "Place and climate": "GEOGRAPHY",
    }
)
STORED_SECTION_STATE = "CHECKING"


async def stream_stored_answer(
    stream: ExplainerStream, craft_name: str, cited: CitedClaims, *, translation: AnswerTranslation
) -> bool:
    ranked = sorted(cited.views.values(), key=lambda c: (-c.rank, LEVEL_ORDER.get(c.level, 9)))
    findings = [c for c in ranked if c.level != OPEN_QUESTION_LEVEL][:STORED_ANSWER_LIMIT]
    open_questions = [c for c in ranked if c.level == OPEN_QUESTION_LEVEL][:STORED_OPEN_QUESTION_LIMIT]
    if not findings and not open_questions:
        return False
    if stream.language != CANONICAL_LANGUAGE:
        await stream.status("TRANSLATING")
    groups: dict[str, list[ClaimView]] = {}
    for view in order_claims(findings):
        groups.setdefault(section_heading(view.concept_type), []).append(view)
    for order, (heading, views) in enumerate(groups.items(), start=1):
        spec = SectionSpec(
            id=f"s{order}",
            discipline=HEADING_DISCIPLINES.get(heading, FALLBACK_DISCIPLINE),
            title=heading,
            order=order,
        )
        await _stored_section(stream, spec, views, cited, translation=translation)
    sentences = [cited_sentence(f"open.{n}", _kept(view), cited) for n, view in enumerate(open_questions, 1)]
    if stream.language != CANONICAL_LANGUAGE and sentences:
        sentences = await translated_sentences(
            sentences, language=stream.language, translation=translation, claim_texts=_texts(cited)
        )
    await stream.open_questions(sentences, cited.sources)
    await stream.emit("follow_ups", {"items": stored_follow_ups(craft_name, list(groups))})
    return True


async def _stored_section(
    stream: ExplainerStream,
    spec: SectionSpec,
    views: Sequence[ClaimView],
    cited: CitedClaims,
    *,
    translation: AnswerTranslation,
) -> None:
    await stream.section_started(spec, titles={}, state=STORED_SECTION_STATE)
    block = prose_block(block_id(spec.id, 1), [_kept(view) for view in views], cited)
    if stream.language != CANONICAL_LANGUAGE:
        payload = block.model_dump(mode="json", by_alias=True)
        shown = await translated_block(
            payload, language=stream.language, translation=translation, claim_texts=_texts(cited)
        )
        block = type(block).model_validate(shown)
    await stream.blocks(spec.id, [block], cited.sources)
    await stream.section_done(spec.id, searched=None)


def _kept(view: ClaimView) -> KeptSentence:
    return KeptSentence(view.text, (view.id,), (), view.level == OPEN_QUESTION_LEVEL)


def _texts(cited: CitedClaims) -> dict[uuid.UUID, str]:
    return {claim_id: view.text for claim_id, view in cited.views.items()}
