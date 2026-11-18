from __future__ import annotations

from typing import Literal

from app.models.enums import (
    COVERAGE_CLASSES,
    ENVIRONMENT_FACTORS,
    MATERIAL_ROLES,
    PLACE_ROLES,
    QUOTE_CHECKS,
    SENSITIVITIES,
    SOURCE_KINDS,
)
from app.research.chapter_keys import CHAPTER_KEYS, PICTURE_PLACEMENTS

__all__ = [
    "CENTRE_ROLES",
    "CHAPTER_KEYS",
    "COVERAGE_CLASSES",
    "CURATED_MATERIAL_ROLES",
    "CURATED_SOURCE_KINDS",
    "CURATOR",
    "DOSSIER_SCHEMA_VERSION",
    "ENVIRONMENT_FACTORS",
    "FAMILY_CENTRE_KINDS",
    "GI_RECORD_SOURCE_KINDS",
    "GROUP_KINDS",
    "INDIA",
    "INDIAN_DISTRICT_PLACE_KINDS",
    "PICTURE_PLACEMENTS",
    "PLACE_KINDS",
    "PLACE_ROLES",
    "QUOTE_RESULTS",
    "READ_ROUTES",
    "SCOPES",
    "SOURCE_ACCESS",
    "SOURCE_SUB_KINDS",
    "SUBJECT_TYPES",
    "WHY_DISCIPLINES",
    "ChapterKey",
    "CoverageClass",
    "CuratedMaterialRole",
    "CuratedSourceKind",
    "EnvironmentFactor",
    "GroupKind",
    "PictureRole",
    "PlaceKind",
    "PlaceRole",
    "QuoteResult",
    "ReadRoute",
    "Scope",
    "Sensitivity",
    "SourceAccess",
    "SourceSubKind",
    "SubjectType",
]

DOSSIER_SCHEMA_VERSION = 2
CURATOR = "claude-code"
CURATED_SOURCE_KINDS = tuple(kind for kind in SOURCE_KINDS if kind != "FIELD_TESTIMONY")
SOURCE_SUB_KINDS = ("THESIS", "MUSEUM_RECORD", "NGO_REPORT", "NEWS")
SOURCE_ACCESS = ("OPEN", "ABSTRACT_ONLY", "RESTRICTED")
SUBJECT_TYPES = ("CRAFT", "STAGE", "MATERIAL", "PLACE", "TOOL", "COMMUNITY", "TERM")
PLACE_KINDS = ("VILLAGE", "TOWN", "DISTRICT", "STATE", "COUNTRY", "REGION", "RIVER")
INDIAN_DISTRICT_PLACE_KINDS = ("VILLAGE", "TOWN", "DISTRICT")
CENTRE_ROLES = ("PRACTISED", "HISTORIC_CENTRE")
FAMILY_CENTRE_KINDS = ("STATE", "REGION")
GROUP_KINDS = ("COMMUNITY", "PERSON", "ORGANISATION")
CURATED_MATERIAL_ROLES = tuple(role for role in MATERIAL_ROLES if role != "TOOL")
GI_RECORD_SOURCE_KINDS = ("GI_JOURNAL", "GOVERNMENT_REPORT")
QUOTE_RESULTS = tuple(check for check in QUOTE_CHECKS if check != "NA")
READ_ROUTES = ("LIVE", "ARCHIVE")
INDIA = "India"
SCOPES = ("CRAFT", "FAMILY", "CATEGORY")
WHY_DISCIPLINES = ("CHEMISTRY", "MATERIALS", "PHYSICS", "BOTANY", "PROCESS")

CoverageClass = Literal[*COVERAGE_CLASSES]
CuratedSourceKind = Literal[*CURATED_SOURCE_KINDS]
SourceSubKind = Literal[*SOURCE_SUB_KINDS]
SourceAccess = Literal[*SOURCE_ACCESS]
SubjectType = Literal[*SUBJECT_TYPES]
PlaceKind = Literal[*PLACE_KINDS]
PlaceRole = Literal[*PLACE_ROLES]
GroupKind = Literal[*GROUP_KINDS]
CuratedMaterialRole = Literal[*CURATED_MATERIAL_ROLES]
EnvironmentFactor = Literal[*ENVIRONMENT_FACTORS]
QuoteResult = Literal[*QUOTE_RESULTS]
Scope = Literal[*SCOPES]
ReadRoute = Literal[*READ_ROUTES]
Sensitivity = Literal[*SENSITIVITIES]
ChapterKey = Literal[*CHAPTER_KEYS]
PictureRole = Literal[*PICTURE_PLACEMENTS]
