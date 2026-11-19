from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import Field

from .article_sections import ArticleSection
from .base import ContractModel
from .crafts import CraftRef
from .knowledge_api import (
    ATTRIBUTION,
    KNOWLEDGE_API_SCHEMA_VERSION,
    ComponentSubject,
    Fact,
    FactSource,
    SchemaVersion,
)
from .vocabulary import Discipline

__all__ = ["CraftExport", "ExportedComponent"]


class ExportedComponent(ContractModel):
    label: str
    kind: str
    title: str
    description: str
    field: Discipline
    fields: list[Discipline]
    craft_slug: str | None
    subjects: list[ComponentSubject]
    claim_ids: list[uuid.UUID] = Field(min_length=1)
    spec: dict[str, Any]


class CraftExport(ContractModel):
    schema_version: SchemaVersion = KNOWLEDGE_API_SCHEMA_VERSION
    craft: CraftRef
    curation_version: int | None = Field(ge=1)
    exported_at: datetime
    facts: list[Fact]
    sources: list[FactSource]
    sections: list[ArticleSection]
    components: list[ExportedComponent]
    page_url: str
    attribution: str = ATTRIBUTION
