from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Literal

from app.core.errors import InvalidInput
from app.models.enums import (
    ANSWER_MODES,
    CHUNK_ACLS,
    CONCEPT_TYPES,
    ENV_STATS,
    EVIDENCE_LEVELS,
    LIVE_TIERS,
    MATERIAL_KINDS,
    MATERIAL_ROLES,
    MEDIA_KINDS,
    QUOTE_CHECKS,
    REACTION_KINDS,
    RELIABILITIES,
    SOURCE_KINDS,
    SOURCE_RELATIONS,
    STAGE_TYPES,
)

__all__ = [
    "ANSWER_LANGUAGES",
    "ANSWER_LANGUAGE_SPECS",
    "CANONICAL_LANGUAGE",
    "EVIDENCE_LABELS",
    "LABEL_LEVELS",
    "LEVEL_ORDER",
    "RETRIEVAL_TIERS",
    "RIGHT_TO_LEFT_SCRIPTS",
    "SHOWN_LEVELS",
    "STORED_TIERS",
    "AnswerLanguage",
    "AnswerLanguageSpec",
    "AnswerMode",
    "ChunkAcl",
    "EnvStat",
    "EvidenceLabel",
    "EvidenceLevel",
    "FacetType",
    "LiveTier",
    "MaterialKind",
    "MaterialRole",
    "MediaKind",
    "QuoteCheck",
    "ReactionKind",
    "RetrievalTier",
    "ShownLevel",
    "SourceRelation",
    "SourceType",
    "StageType",
    "TextDirection",
    "TrustTier",
    "language_option",
    "text_direction",
    "weakest_level",
]

STORED_TIERS = ("T0", "T1", "T2")
RETRIEVAL_TIERS = (*STORED_TIERS, *LIVE_TIERS)
SHOWN_LEVELS = (*EVIDENCE_LEVELS, "UNAVAILABLE")
EVIDENCE_LABELS = ("QUOTED", "INFERRED")
LABEL_LEVELS = {"QUOTED": "PROVISIONAL", "INFERRED": "HYPOTHESIS"}
LEVEL_ORDER = {level: rank for rank, level in enumerate(EVIDENCE_LEVELS)}


@dataclass(frozen=True)
class AnswerLanguageSpec:
    label: str
    autonym: str
    script: str


ANSWER_LANGUAGE_SPECS: Mapping[str, AnswerLanguageSpec] = MappingProxyType(
    {
        "en": AnswerLanguageSpec("English", "English", "Latn"),
        "hi": AnswerLanguageSpec("Hindi", "हिन्दी", "Deva"),
        "bn": AnswerLanguageSpec("Bengali", "বাংলা", "Beng"),
        "ta": AnswerLanguageSpec("Tamil", "தமிழ்", "Taml"),
        "te": AnswerLanguageSpec("Telugu", "తెలుగు", "Telu"),
        "mr": AnswerLanguageSpec("Marathi", "मराठी", "Deva"),
        "gu": AnswerLanguageSpec("Gujarati", "ગુજરાતી", "Gujr"),
        "kn": AnswerLanguageSpec("Kannada", "ಕನ್ನಡ", "Knda"),
        "ml": AnswerLanguageSpec("Malayalam", "മലയാളം", "Mlym"),
        "or": AnswerLanguageSpec("Odia", "ଓଡ଼ିଆ", "Orya"),
        "pa": AnswerLanguageSpec("Punjabi", "ਪੰਜਾਬੀ", "Guru"),
        "as": AnswerLanguageSpec("Assamese", "অসমীয়া", "Beng"),
        "ur": AnswerLanguageSpec("Urdu", "اردو", "Arab"),
    }
)
ANSWER_LANGUAGES = tuple(ANSWER_LANGUAGE_SPECS)
CANONICAL_LANGUAGE = "en"
RIGHT_TO_LEFT_SCRIPTS = frozenset({"Arab"})
TEXT_DIRECTIONS = ("ltr", "rtl")

AnswerLanguage = Literal[*ANSWER_LANGUAGES]
TextDirection = Literal[*TEXT_DIRECTIONS]
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
StageType = Literal[*STAGE_TYPES]
MaterialKind = Literal[*MATERIAL_KINDS]
MaterialRole = Literal[*MATERIAL_ROLES]
ReactionKind = Literal[*REACTION_KINDS]
EnvStat = Literal[*ENV_STATS]
MediaKind = Literal[*MEDIA_KINDS]


def weakest_level(levels: Iterable[str]) -> str:
    given = list(levels)
    if not given:
        raise InvalidInput("A level needs at least one input level")
    unknown = sorted({level for level in given if level not in LEVEL_ORDER})
    if unknown:
        raise InvalidInput(f"Unknown evidence levels: {', '.join(unknown)}")
    return max(given, key=LEVEL_ORDER.__getitem__)


def text_direction(language: str) -> TextDirection:
    spec = ANSWER_LANGUAGE_SPECS.get(language)
    if spec is None:
        raise InvalidInput(f"Unknown answer language {language!r}")
    return "rtl" if spec.script in RIGHT_TO_LEFT_SCRIPTS else "ltr"


def language_option(language: str) -> dict[str, str]:
    spec = ANSWER_LANGUAGE_SPECS.get(language)
    if spec is None:
        raise InvalidInput(f"Unknown answer language {language!r}")
    return {
        "code": language,
        "label": spec.label,
        "autonym": spec.autonym,
        "script": spec.script,
        "direction": text_direction(language),
    }
