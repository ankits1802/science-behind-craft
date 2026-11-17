from __future__ import annotations

import uuid
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from .knowledge_pieces import KnowledgePiece, ReuseAsk, reuse_refusal

__all__ = ["PIECE_BLOCK_ORDER", "ClaimState", "piece_group_key", "reusable_groups", "visible_as_cited"]

PIECE_BLOCK_ORDER = ("process_ladder", "prose", "images")


@dataclass(frozen=True)
class ClaimState:
    level: str
    citation_ids: frozenset[str]


def visible_as_cited(piece: KnowledgePiece, current: Mapping[uuid.UUID, ClaimState]) -> set[uuid.UUID]:
    cited: dict[uuid.UUID, set[str]] = {}
    levels: dict[uuid.UUID, set[str]] = {}
    for citation in piece.payload.citations():
        claim_id = uuid.UUID(citation.claim_id)
        cited.setdefault(claim_id, set()).add(citation.id)
        levels.setdefault(claim_id, set()).add(citation.level)
    return {
        claim_id
        for claim_id, citation_ids in cited.items()
        if claim_id in current
        and citation_ids <= current[claim_id].citation_ids
        and levels[claim_id] == {current[claim_id].level}
    }


def piece_group_key(piece: KnowledgePiece) -> tuple[str, uuid.UUID]:
    return piece.facet, piece.created_from_answer_id or piece.id


def reusable_groups(
    pieces: Sequence[KnowledgePiece], ask: ReuseAsk, current: Mapping[uuid.UUID, ClaimState]
) -> list[tuple[KnowledgePiece, ...]]:
    groups: dict[tuple[str, uuid.UUID], list[KnowledgePiece]] = {}
    for piece in pieces:
        if piece.facet == ask.facet:
            groups.setdefault(piece_group_key(piece), []).append(piece)
    return [
        tuple(sorted(group, key=lambda piece: PIECE_BLOCK_ORDER.index(piece.kind)))
        for group in groups.values()
        if all(reuse_refusal(piece, ask, visible_as_cited(piece, current)) is None for piece in group)
    ]
