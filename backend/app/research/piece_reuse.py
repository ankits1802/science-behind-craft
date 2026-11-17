from __future__ import annotations

import re
import uuid
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from .knowledge_pieces import KnowledgePiece, ReuseAsk, reuse_refusal

__all__ = [
    "PIECE_BLOCK_ORDER",
    "REGION_STORY_FACETS",
    "REGION_STORY_KIND",
    "ClaimState",
    "piece_group_key",
    "reusable_groups",
    "visible_as_cited",
    "with_region_story",
]

REGION_STORY_KIND = "region_story"
REGION_STORY_FACETS = frozenset({"GEOGRAPHY"})
PIECE_BLOCK_ORDER = (
    "process_ladder",
    "prose",
    "region_story",
    "map_layer",
    "seasons",
    "supply_map",
    "reaction_player",
    "material_card",
    "molecule_3d",
    "expert_view",
    "images",
)
DIGITS = re.compile(r"(\d+)")


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
        tuple(sorted(group, key=_reading_order))
        for group in groups.values()
        if all(reuse_refusal(piece, ask, visible_as_cited(piece, current)) is None for piece in group)
    ]


def with_region_story(
    group: Sequence[KnowledgePiece],
    regions: Sequence[KnowledgePiece],
    *,
    depth: str,
    current: Mapping[uuid.UUID, ClaimState],
) -> tuple[KnowledgePiece, ...]:
    facet = group[0].facet
    usable = [
        piece
        for piece in regions
        if piece.kind == REGION_STORY_KIND
        and piece.craft_id is None
        and reuse_refusal(
            piece,
            ReuseAsk(craft_id=None, facet=facet, topic_key=piece.topic_key, depth=depth),
            visible_as_cited(piece, current),
        )
        is None
    ]
    if not usable:
        return tuple(group)
    answer = group[0].created_from_answer_id
    same = [piece for piece in usable if answer is not None and piece.created_from_answer_id == answer]
    chosen = (same or usable)[0]
    return tuple(sorted([*group, chosen], key=_reading_order))


def _reading_order(piece: KnowledgePiece) -> tuple[int, list[tuple[int, int, str]]]:
    shown = [
        (0, int(part), "") if part.isdigit() else (1, 0, part) for part in DIGITS.split(piece.payload.id)
    ]
    return PIECE_BLOCK_ORDER.index(piece.kind), shown
