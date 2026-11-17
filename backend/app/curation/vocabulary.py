from __future__ import annotations

from typing import Literal

from app.models.enums import (
    COVERAGE_CLASSES,
    MATERIAL_ROLES,
    PLACE_ROLES,
    QUOTE_CHECKS,
    SENSITIVITIES,
    SOURCE_KINDS,
)

__all__ = [
    "CENTRE_ROLES",
    "COVERAGE_CLASSES",
    "CURATED_MATERIAL_ROLES",
    "CURATED_SOURCE_KINDS",
    "CURATOR",
    "DOSSIER_SCHEMA_VERSION",
    "ENVIRONMENT_FACTORS",
    "GI_RECORD_SOURCE_KINDS",
    "GROUP_KINDS",
    "INDIA",
    "INDIAN_DISTRICT_PLACE_KINDS",
    "PLACE_KINDS",
    "PLACE_ROLES",
    "QUOTE_RESULTS",
    "READ_ROUTES",
    "SOURCE_ACCESS",
    "SOURCE_SUB_KINDS",
    "SUBJECT_TYPES",
    "CoverageClass",
    "CuratedMaterialRole",
    "CuratedSourceKind",
    "EnvironmentFactor",
    "GroupKind",
    "PlaceKind",
    "PlaceRole",
    "QuoteResult",
    "ReadRoute",
    "Sensitivity",
    "SourceAccess",
    "SourceSubKind",
    "SubjectType",
]

DOSSIER_SCHEMA_VERSION = 1
CURATOR = "claude-code"
CURATED_SOURCE_KINDS = tuple(kind for kind in SOURCE_KINDS if kind != "FIELD_TESTIMONY")
SOURCE_SUB_KINDS = ("THESIS", "MUSEUM_RECORD", "NGO_REPORT", "NEWS")
SOURCE_ACCESS = ("OPEN", "ABSTRACT_ONLY", "RESTRICTED")
SUBJECT_TYPES = ("CRAFT", "STAGE", "MATERIAL", "PLACE", "TOOL", "COMMUNITY", "TERM")
PLACE_KINDS = ("VILLAGE", "TOWN", "DISTRICT", "STATE", "COUNTRY", "REGION", "RIVER")
INDIAN_DISTRICT_PLACE_KINDS = ("VILLAGE", "TOWN", "DISTRICT")
CENTRE_ROLES = ("PRACTISED", "HISTORIC_CENTRE")
GROUP_KINDS = ("COMMUNITY", "PERSON", "ORGANISATION")
CURATED_MATERIAL_ROLES = tuple(role for role in MATERIAL_ROLES if role != "TOOL")
ENVIRONMENT_FACTORS = ("WATER", "SOIL", "CLIMATE", "LANDFORM", "VEGETATION", "OTHER")
GI_RECORD_SOURCE_KINDS = ("GI_JOURNAL", "GOVERNMENT_REPORT")
QUOTE_RESULTS = tuple(check for check in QUOTE_CHECKS if check != "NA")
READ_ROUTES = ("LIVE", "ARCHIVE")
INDIA = "India"

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
ReadRoute = Literal[*READ_ROUTES]
Sensitivity = Literal[*SENSITIVITIES]
