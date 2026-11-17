from __future__ import annotations

import re
from collections.abc import Mapping
from types import MappingProxyType
from typing import Annotated

from pydantic import AfterValidator, Field

from .limits import SENTENCE_MAX_CHARS

__all__ = [
    "CRAFT_SLUG_PATTERN",
    "ID_PATTERNS",
    "SUBJECT_KINDS",
    "ClaimId",
    "ClaimIds",
    "CommunityId",
    "MaterialId",
    "NameList",
    "NameText",
    "PictureId",
    "PlaceId",
    "QuestionId",
    "ReactionId",
    "SentenceText",
    "SourceId",
    "StageId",
    "TermId",
    "ToolId",
    "distinct",
    "id_kind",
]

CRAFT_SLUG_PATTERN = r"^[A-Za-z0-9]+(?:-[A-Za-z0-9]+)*$"
ID_PATTERNS: Mapping[str, str] = MappingProxyType(
    {
        "source": r"^S\d{2,3}$",
        "claim": r"^C\d{3,4}$",
        "place": r"^L\d{2,3}$",
        "community": r"^G\d{2,3}$",
        "stage": r"^P\d{2,3}$",
        "material": r"^M\d{2,3}$",
        "tool": r"^T\d{2,3}$",
        "reaction": r"^R\d{2,3}$",
        "term": r"^W\d{2,3}$",
        "picture": r"^I\d{2,3}$",
        "question": r"^O\d{2,3}$",
    }
)
SUBJECT_KINDS: Mapping[str, str] = MappingProxyType(
    {
        "STAGE": "stage",
        "MATERIAL": "material",
        "PLACE": "place",
        "TOOL": "tool",
        "COMMUNITY": "community",
        "TERM": "term",
    }
)


def distinct(values: list[str]) -> list[str]:
    repeated = sorted({value for index, value in enumerate(values) if value in values[:index]})
    if repeated:
        raise ValueError(f"lists {', '.join(repeated)} more than once")
    return values


def id_kind(value: str) -> str | None:
    return next((kind for kind, pattern in ID_PATTERNS.items() if re.fullmatch(pattern, value)), None)


SourceId = Annotated[str, Field(pattern=ID_PATTERNS["source"])]
ClaimId = Annotated[str, Field(pattern=ID_PATTERNS["claim"])]
PlaceId = Annotated[str, Field(pattern=ID_PATTERNS["place"])]
CommunityId = Annotated[str, Field(pattern=ID_PATTERNS["community"])]
StageId = Annotated[str, Field(pattern=ID_PATTERNS["stage"])]
MaterialId = Annotated[str, Field(pattern=ID_PATTERNS["material"])]
ToolId = Annotated[str, Field(pattern=ID_PATTERNS["tool"])]
ReactionId = Annotated[str, Field(pattern=ID_PATTERNS["reaction"])]
TermId = Annotated[str, Field(pattern=ID_PATTERNS["term"])]
PictureId = Annotated[str, Field(pattern=ID_PATTERNS["picture"])]
QuestionId = Annotated[str, Field(pattern=ID_PATTERNS["question"])]
ClaimIds = Annotated[list[ClaimId], Field(min_length=1), AfterValidator(distinct)]
NameText = Annotated[str, Field(min_length=1, max_length=300)]
NameList = Annotated[list[NameText], AfterValidator(distinct)]
SentenceText = Annotated[str, Field(min_length=1, max_length=SENTENCE_MAX_CHARS)]
