from __future__ import annotations

import hashlib
import itertools
import json
import uuid
from collections.abc import Collection
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Literal, Self

from pydantic import AwareDatetime, Field, TypeAdapter, model_validator

from .base import ContractModel
from .blocks import BlockBase, ImagesBlock, ReuseMarker
from .depth import depth_at_least
from .explainer import BUILT_BLOCK_KINDS, Block
from .subject_keys import TopicKey
from .vocabulary import CANONICAL_LANGUAGE, AnswerLanguage, BlockKind, Depth, Discipline

__all__ = [
    "PIECE_SCHEMA_VERSION",
    "PIECE_SENTENCE_PREFIX_CHARS",
    "PIECE_STALE_CHANGES",
    "PLACEMENT_FIELDS",
    "REUSE_REFUSALS",
    "KnowledgePiece",
    "PieceSlot",
    "ReuseAsk",
    "knowledge_piece",
    "piece_content_hash",
    "piece_text",
    "placed_block",
    "rests_on",
    "reuse_refusal",
]

PIECE_SCHEMA_VERSION = 1
PIECE_STALE_CHANGES = ("RETRACTED", "LEVEL_CHANGED", "HIDDEN", "TEXT_CHANGED")
PLACEMENT_FIELDS = frozenset({"id", "reuse"})
REUSE_REFUSALS = ("CRAFT", "FACET", "TOPIC", "DEPTH", "STALE", "SUPERSEDED", "CLAIM_NOT_VISIBLE")
PIECE_SENTENCE_PREFIX_CHARS = 12
SENTENCES_FIELD = "sentences"
BLOCKS = TypeAdapter(Block)

ReuseRefusal = Literal[*REUSE_REFUSALS]


class KnowledgePiece(ContractModel):
    schema_version: Literal[1]
    id: uuid.UUID
    craft_id: uuid.UUID | None
    kind: BlockKind
    facet: Discipline
    topic_key: TopicKey
    language: AnswerLanguage
    depth: Depth
    payload: Block
    claim_ids: list[uuid.UUID] = Field(min_length=1)
    source_ids: list[str] = Field(min_length=1)
    content_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    created_from_answer_id: uuid.UUID | None
    created_at: AwareDatetime
    stale_since: AwareDatetime | None
    superseded_by_id: uuid.UUID | None

    @model_validator(mode="after")
    def _payload_and_what_it_rests_on_agree(self) -> Self:
        if self.language != CANONICAL_LANGUAGE:
            raise ValueError(
                f"piece {self.id} is stored in {CANONICAL_LANGUAGE}; translations are cached apart"
            )
        if self.payload.kind != self.kind or self.payload.reuse is not None:
            raise ValueError(f"piece {self.id} stores a {self.kind} block as built, with no reuse mark")
        if self.kind not in BUILT_BLOCK_KINDS:
            raise ValueError(f"piece {self.id} stores a {self.kind} block, which is not built yet")
        cited = sorted({uuid.UUID(claim) for claim in self.payload.cited_claim_ids()})
        if self.claim_ids != cited:
            raise ValueError(f"piece {self.id} lists the claims its block cites, once each, sorted")
        if self.source_ids != sorted(self.payload.cited_source_ids()):
            raise ValueError(f"piece {self.id} lists the sources its block cites, once each, sorted")
        if self.content_hash != piece_content_hash(self.payload):
            raise ValueError(f"piece {self.id} content hash does not match its block")
        if self.superseded_by_id == self.id:
            raise ValueError(f"piece {self.id} cannot supersede itself")
        return self


class ReuseAsk(ContractModel):
    craft_id: uuid.UUID | None
    facet: Discipline
    topic_key: TopicKey
    depth: Depth


def piece_content_hash(block: BlockBase) -> str:
    plain = block.model_dump(mode="json", by_alias=True, exclude=PLACEMENT_FIELDS)
    canonical = json.dumps(plain, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def rests_on(piece: KnowledgePiece, claim_ids: Collection[uuid.UUID]) -> bool:
    return not set(claim_ids).isdisjoint(piece.claim_ids)


def reuse_refusal(
    piece: KnowledgePiece, ask: ReuseAsk, visible_claim_ids: Collection[uuid.UUID]
) -> ReuseRefusal | None:
    matches = (
        ("CRAFT", piece.craft_id == ask.craft_id),
        ("FACET", piece.facet == ask.facet),
        ("TOPIC", piece.topic_key == ask.topic_key),
        ("DEPTH", depth_at_least(piece.depth, ask.depth)),
        ("STALE", piece.stale_since is None),
        ("SUPERSEDED", piece.superseded_by_id is None),
        ("CLAIM_NOT_VISIBLE", set(piece.claim_ids) <= set(visible_claim_ids)),
    )
    return next((refusal for refusal, holds in matches if not holds), None)


@dataclass(frozen=True)
class PieceSlot:
    craft_id: uuid.UUID | None
    facet: str
    topic_key: str
    depth: str


def knowledge_piece(
    block: BlockBase,
    slot: PieceSlot,
    *,
    piece_id: uuid.UUID,
    answer_id: uuid.UUID | None,
    created_at: datetime,
) -> KnowledgePiece:
    payload = _piece_sentence_ids(block.model_dump(mode="json", by_alias=True) | {"reuse": None}, piece_id)
    stored = BLOCKS.validate_python(payload)
    return KnowledgePiece(
        schema_version=PIECE_SCHEMA_VERSION,
        id=piece_id,
        craft_id=slot.craft_id,
        kind=stored.kind,
        facet=slot.facet,
        topic_key=slot.topic_key,
        language=CANONICAL_LANGUAGE,
        depth=slot.depth,
        payload=stored,
        claim_ids=sorted({uuid.UUID(claim) for claim in stored.cited_claim_ids()}),
        source_ids=sorted(stored.cited_source_ids()),
        content_hash=piece_content_hash(stored),
        created_from_answer_id=answer_id,
        created_at=created_at,
        stale_since=None,
        superseded_by_id=None,
    )


def placed_block(piece: KnowledgePiece, block_id: str) -> Block:
    marker = ReuseMarker(piece_id=piece.id, stored_at=piece.created_at)
    return piece.payload.model_copy(update={"id": block_id, "reuse": marker})


def piece_text(block: BlockBase) -> str:
    texts = [sentence.text for sentence in block.cited_sentences()]
    if isinstance(block, ImagesBlock):
        texts += [item.media.title for item in block.items]
    return " ".join(texts)


def _piece_sentence_ids(payload: dict[str, Any], piece_id: uuid.UUID) -> dict[str, Any]:
    prefix = f"p{piece_id.hex[:PIECE_SENTENCE_PREFIX_CHARS]}"
    counter = itertools.count(1)

    def renamed(value: Any, key: str | None = None) -> Any:
        if isinstance(value, dict):
            return {name: renamed(item, name) for name, item in value.items()}
        if isinstance(value, list) and key == SENTENCES_FIELD:
            return [renamed(item) | {"id": f"{prefix}.{next(counter)}"} for item in value]
        if isinstance(value, list):
            return [renamed(item) for item in value]
        return value

    return renamed(payload)
