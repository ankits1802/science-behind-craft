from __future__ import annotations

from collections.abc import Iterable, Mapping
from types import MappingProxyType
from typing import Literal

from app.core.errors import InvalidInput
from app.models.enums import (
    ANSWER_MODES,
    CHUNK_ACLS,
    CONCEPT_TYPES,
    EVIDENCE_LEVELS,
    LIVE_TIERS,
    QUOTE_CHECKS,
    RELIABILITIES,
    SOURCE_KINDS,
    SOURCE_RELATIONS,
)

__all__ = [
    "ANSWER_LANGUAGES",
    "ANSWER_LANGUAGE_LABELS",
    "EVIDENCE_LABELS",
    "LABEL_LEVELS",
    "LEVEL_ORDER",
    "RETRIEVAL_TIERS",
    "SHOWN_LEVELS",
    "STORED_TIERS",
    "AnswerLanguage",
    "AnswerMode",
    "ChunkAcl",
    "EvidenceLabel",
    "EvidenceLevel",
    "FacetType",
    "LiveTier",
    "QuoteCheck",
    "RetrievalTier",
    "ShownLevel",
    "SourceRelation",
    "SourceType",
    "TrustTier",
    "weakest_level",
]

STORED_TIERS = ("T0", "T1", "T2")
RETRIEVAL_TIERS = (*STORED_TIERS, *LIVE_TIERS)
SHOWN_LEVELS = (*EVIDENCE_LEVELS, "UNAVAILABLE")
EVIDENCE_LABELS = ("QUOTED", "INFERRED")
LABEL_LEVELS = {"QUOTED": "PROVISIONAL", "INFERRED": "HYPOTHESIS"}
LEVEL_ORDER = {level: rank for rank, level in enumerate(EVIDENCE_LEVELS)}
ANSWER_LANGUAGE_LABELS: Mapping[str, str] = MappingProxyType({"en": "English"})
ANSWER_LANGUAGES = tuple(ANSWER_LANGUAGE_LABELS)

AnswerLanguage = Literal[*ANSWER_LANGUAGES]
AnswerMode = Literal[*ANSWER_MODES]
ChunkAcl = Literal[*CHUNK_ACLS]
EvidenceLevel = Literal[*EVIDENCE_LEVELS]
ShownLevel = Literal[*SHOWN_LEVELS]
RetrievalTier = Literal[*RETRIEVAL_TIERS]
LiveTier = Literal[*LIVE_TIERS]
TrustTier = Literal[*RELIABILITIES]
SourceType = Literal[*SOURCE_KINDS]
FacetType = Literal[*CONCEPT_TYPES]
QuoteCheck = Literal[*QUOTE_CHECKS]
SourceRelation = Literal[*SOURCE_RELATIONS]
EvidenceLabel = Literal[*EVIDENCE_LABELS]


def weakest_level(levels: Iterable[str]) -> str:
    given = list(levels)
    if not given:
        raise InvalidInput("A level needs at least one input level")
    unknown = sorted({level for level in given if level not in LEVEL_ORDER})
    if unknown:
        raise InvalidInput(f"Unknown evidence levels: {', '.join(unknown)}")
    return max(given, key=LEVEL_ORDER.__getitem__)
