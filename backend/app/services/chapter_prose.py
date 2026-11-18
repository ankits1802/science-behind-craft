from __future__ import annotations

import uuid
from collections.abc import Collection

from app.research.blocks import ExplainerSentence, ProseBlock
from app.research.chapter_keys import DISCIPLINE_CHAPTERS
from app.research.craft_page import OverviewSection
from app.research.vocabulary import FACT_LEVELS, weakest_level

from .chapter_context import ChapterContext

__all__ = ["chapter_disciplines", "piece_sentences", "prose_blocks"]


def chapter_disciplines(chapter: str) -> list[str]:
    return [discipline for discipline, key in DISCIPLINE_CHAPTERS.items() if key == chapter]


def prose_blocks(
    ctx: ChapterContext, chapter: str, sections: Collection[OverviewSection]
) -> list[ProseBlock]:
    wanted = chapter_disciplines(chapter)
    curated = ctx.records.curated
    blocks: list[ProseBlock] = []
    if curated is not None:
        for section in curated.overview.sections:
            if section.discipline in wanted:
                sentences = piece_sentences(ctx, section.piece_id)
                blocks += _prose(f"{chapter}.{section.discipline.lower()}", sentences)
        return blocks
    for found in sections:
        if found.discipline in wanted:
            claim_ids = [claim_id for sentence in found.sentences for claim_id in sentence.claim_ids]
            blocks += _prose(
                f"{chapter}.{found.discipline.lower()}", ctx.facts(claim_ids, found.discipline.lower())
            )
    return blocks


def piece_sentences(ctx: ChapterContext, piece_id: uuid.UUID) -> list[ExplainerSentence]:
    piece = ctx.records.pieces.get(piece_id)
    if piece is None or not isinstance(piece.payload, ProseBlock):
        return []
    shown = []
    for sentence in piece.payload.sentences:
        claim_ids = [uuid.UUID(citation.claim_id) for citation in sentence.citations]
        if not ctx.visible.all_shown(claim_ids):
            continue
        level = weakest_level(ctx.visible.levels[claim_id] for claim_id in claim_ids)
        if level in FACT_LEVELS:
            shown.append(
                sentence if sentence.level == level else sentence.model_copy(update={"level": level})
            )
    return shown


def _prose(block_id: str, sentences: list[ExplainerSentence]) -> list[ProseBlock]:
    if not sentences:
        return []
    return [ProseBlock(id=block_id, kind="prose", version=1, reuse=None, sentences=sentences)]
