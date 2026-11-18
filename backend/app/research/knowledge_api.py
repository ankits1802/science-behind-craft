from __future__ import annotations

import uuid
from typing import Literal

from pydantic import Field

from .article_sections import ArticleSection
from .base import ContractModel
from .crafts import QUESTION_MAX_CHARS, SLUG_MAX_CHARS, CraftRef
from .vocabulary import Discipline, EvidenceLevel

__all__ = [
    "ATTRIBUTION",
    "COMPONENTS_LIMIT_MAX",
    "FACTS_LIMIT_DEFAULT",
    "FACTS_LIMIT_MAX",
    "KNOWLEDGE_API_SCHEMA_VERSION",
    "ComponentSummary",
    "CraftComponents",
    "CraftFacts",
    "CraftSection",
    "Fact",
    "FactCitation",
    "FactSource",
    "FieldInfo",
    "FieldList",
    "FoundCraft",
    "FoundCrafts",
]

KNOWLEDGE_API_SCHEMA_VERSION = 1
FACTS_LIMIT_DEFAULT = 20
FACTS_LIMIT_MAX = 50
COMPONENTS_LIMIT_MAX = 100
ATTRIBUTION = (
    "KalaVigyan, Centre of Excellence for Unified AI-Enabled Craft Ecosystem Platform, IIT Kharagpur. "
    "Name KalaVigyan and the Centre, and link the craft's page, wherever this content is shown."
)

SchemaVersion = Literal[1]


class FieldInfo(ContractModel):
    field: Discipline
    title: str
    covers: str
    chapter: str


class FieldList(ContractModel):
    schema_version: SchemaVersion = KNOWLEDGE_API_SCHEMA_VERSION
    fields: list[FieldInfo]


class FoundCraft(ContractModel):
    craft: CraftRef
    score: float = Field(ge=0.0, le=1.0)
    page_url: str


class FoundCrafts(ContractModel):
    schema_version: SchemaVersion = KNOWLEDGE_API_SCHEMA_VERSION
    query: str = Field(min_length=1, max_length=QUESTION_MAX_CHARS)
    crafts: list[FoundCraft]


class FactCitation(ContractModel):
    source_id: str
    quote: str | None
    locator: str | None


class FactSource(ContractModel):
    id: str
    kind: str
    title: str
    authors: list[str]
    year: int | None
    doi: str | None
    url: str | None
    publisher: str | None
    licence: str | None
    attribution: str | None


class Fact(ContractModel):
    id: uuid.UUID
    text: str
    level: EvidenceLevel
    field: Discipline | None
    fields: list[Discipline]
    citations: list[FactCitation] = Field(min_length=1)


class CraftFacts(ContractModel):
    schema_version: SchemaVersion = KNOWLEDGE_API_SCHEMA_VERSION
    craft: CraftRef
    field: Discipline | None
    query: str | None
    facts: list[Fact]
    sources: list[FactSource]
    page_url: str
    attribution: str = ATTRIBUTION


class CraftSection(ContractModel):
    schema_version: SchemaVersion = KNOWLEDGE_API_SCHEMA_VERSION
    craft: CraftRef
    field: Discipline
    section: ArticleSection | None
    page_url: str
    attribution: str = ATTRIBUTION


class ComponentSummary(ContractModel):
    label: str
    title: str
    description: str
    kind: str
    field: Discipline
    fields: list[Discipline]


class CraftComponents(ContractModel):
    schema_version: SchemaVersion = KNOWLEDGE_API_SCHEMA_VERSION
    craft_slug: str | None = Field(max_length=SLUG_MAX_CHARS)
    field: Discipline | None
    components: list[ComponentSummary]
