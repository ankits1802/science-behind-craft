from __future__ import annotations

import uuid
from collections.abc import Mapping
from datetime import UTC, date, datetime
from types import MappingProxyType

from app.data.craft_master_loader import ID_NAMESPACE

__all__ = [
    "CRAFT_LOCATION_ROLES",
    "CURATED_DEPTH",
    "CURATED_PREDICATE",
    "CURATED_PROCESS_NAME",
    "CURATED_PROCESS_VARIANT",
    "CURATED_STATUS",
    "CURATION_ACTOR",
    "CURATION_LEVELS",
    "DISCIPLINE_CONCEPT_TYPES",
    "ENTITY_CONCEPT_TYPES",
    "HYPOTHESIS_LEVEL",
    "MEDIA_PROVIDER",
    "QUOTED_LEVEL",
    "SUPERSEDED_STATUS",
    "TERM_NAME_SEPARATOR",
    "TOOL_MATERIAL_KIND",
    "TOOL_ROLE",
    "WITHDRAWN_STATUS",
    "craft_concept_key",
    "curated_id",
    "day_start",
]

CURATION_ACTOR = "curation"
CURATED_PREDICATE = "states"
CURATED_STATUS = "APPROVED"
SUPERSEDED_STATUS = "SUPERSEDED"
WITHDRAWN_STATUS = "WITHDRAWN"
QUOTED_LEVEL = "PROVISIONAL"
HYPOTHESIS_LEVEL = "HYPOTHESIS"
CURATION_LEVELS = (QUOTED_LEVEL, HYPOTHESIS_LEVEL)
CURATED_DEPTH = "EXPERT"
CURATED_PROCESS_NAME = "Curated process"
CURATED_PROCESS_VARIANT = "curation"
MEDIA_PROVIDER = "curation"
TOOL_ROLE = "TOOL"
TOOL_MATERIAL_KIND = "OTHER"
TERM_NAME_SEPARATOR = ","
CRAFT_LOCATION_ROLES = ("PRACTISED", "ORIGIN", "HISTORIC_CENTRE", "MIGRATED_FROM", "MIGRATED_TO")

ENTITY_CONCEPT_TYPES: Mapping[str, str] = MappingProxyType(
    {
        "STAGE": "PROCESS_STAGE",
        "MATERIAL": "MATERIAL",
        "TOOL": "TOOL",
        "PLACE": "ENVIRONMENTAL_CONDITION",
        "COMMUNITY": "TRADITION",
        "TERM": "CONCEPT",
    }
)
DISCIPLINE_CONCEPT_TYPES: Mapping[str, str] = MappingProxyType(
    {
        "OVERVIEW": "TRADITION",
        "PROCESS": "ARTISAN_ACTION",
        "CHEMISTRY": "MECHANISM",
        "PHYSICS": "MECHANISM",
        "MATERIALS": "PROPERTY",
        "GEOGRAPHY": "ENVIRONMENTAL_CONDITION",
        "GEOLOGY": "ENVIRONMENTAL_CONDITION",
        "CLIMATE": "ENVIRONMENTAL_CONDITION",
        "ECOLOGY": "ENVIRONMENTAL_CONDITION",
        "BOTANY": "PROPERTY",
        "HISTORY": "HISTORICAL_CONTEXT",
        "ECONOMICS": "OUTCOME",
        "DESIGN": "DESIGN_PRINCIPLE",
        "HEALTH": "CONCEPT",
    }
)


def curated_id(slug: str, *parts: str) -> uuid.UUID:
    return uuid.uuid5(ID_NAMESPACE, ":".join(("curation", slug, *parts)))


def craft_concept_key(discipline: str) -> str:
    return f"craft:{discipline}"


def day_start(day: date) -> datetime:
    return datetime(day.year, day.month, day.day, tzinfo=UTC)
