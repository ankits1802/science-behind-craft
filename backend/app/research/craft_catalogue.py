from __future__ import annotations

import json
from typing import Literal

from pydantic import Field

from app.models.enums import COVERAGE_CLASSES, CRAFT_STATUSES, GI_STATUSES

from .base import ContractModel, HttpsUrl

__all__ = [
    "CATALOGUE_SCHEMA_VERSION",
    "CatalogueCategory",
    "CatalogueConcept",
    "CatalogueCraft",
    "CatalogueCraftRecord",
    "CatalogueDepth",
    "CatalogueHero",
    "CatalogueSubCategory",
    "CatalogueSummary",
    "CraftCatalogue",
    "catalogue_text",
]

CATALOGUE_SCHEMA_VERSION = 2


class CatalogueSubCategory(ContractModel):
    id: str
    slug: str
    name: str
    label: str | None
    sort_order: int
    craft_count: int = Field(ge=0)
    reader_count: int = Field(ge=0)


class CatalogueCategory(ContractModel):
    id: str
    slug: str
    name: str
    label: str | None
    palette: str | None
    sort_order: int
    reader_count: int = Field(ge=0)
    sub_categories: list[CatalogueSubCategory]


class CatalogueHero(ContractModel):
    url: HttpsUrl
    width: int | None = Field(ge=1)
    height: int | None = Field(ge=1)
    alt: str = Field(min_length=1)
    author: str = Field(min_length=1)
    licence: str | None
    licence_url: HttpsUrl | None
    site: str = Field(min_length=1)
    page_url: HttpsUrl


class CatalogueDepth(ContractModel):
    coverage: Literal[*COVERAGE_CLASSES] | None
    claims: int = Field(ge=0)
    stages: int = Field(ge=0)
    pictures: int = Field(ge=0)
    places: int = Field(ge=0)


class CatalogueCraft(ContractModel):
    id: str
    slug: str
    name: str
    display_name: str = Field(min_length=1)
    local_name: str | None
    category_id: str | None
    sub_category_id: str | None
    family_label: str | None
    kind_label: str | None
    palette: str | None
    source_serial: int | None
    state_of_origin: list[str]
    state_of_practice: list[str]
    gi_status: Literal[*GI_STATUSES] | None
    gi_year: int | None
    is_catch_all: bool
    craft_code: str | None
    aliases: list[str]
    hero: CatalogueHero | None
    depth: CatalogueDepth


class CatalogueCraftRecord(CatalogueCraft):
    status: Literal[*CRAFT_STATUSES]
    merged_into_id: str | None
    reference_count: int | None = Field(ge=0)


class CatalogueConcept(ContractModel):
    key: str = Field(min_length=1)
    label: str = Field(min_length=1)
    names: list[str]
    craft_slugs: list[str] = Field(min_length=1)


class CatalogueSummary(ContractModel):
    crafts: int = Field(ge=0)
    gi_registered: int = Field(ge=0)
    states: int = Field(ge=0)
    placed: int = Field(ge=0)
    families: int = Field(ge=0)
    kinds: int = Field(ge=0)


class CraftCatalogue(ContractModel):
    schema_version: Literal[2] = CATALOGUE_SCHEMA_VERSION
    version: str
    summary: CatalogueSummary
    categories: list[CatalogueCategory]
    concepts: list[CatalogueConcept]
    crafts: list[CatalogueCraftRecord | CatalogueCraft]


def catalogue_text(catalogue: CraftCatalogue) -> str:
    return json.dumps(catalogue.model_dump(mode="json", by_alias=True), indent=2, ensure_ascii=False) + "\n"
