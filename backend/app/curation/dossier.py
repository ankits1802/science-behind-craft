from __future__ import annotations

import json
from typing import Any, Literal

from pydantic import AwareDatetime, Field

from app.research.base import ContractModel

from .entities import Community, Material, Place, Reaction, Stage, Tool
from .fields import CRAFT_SLUG_PATTERN
from .limits import PICTURES_MAX
from .overview import Overview
from .parts import Claim, Conflict, OpenQuestion, Search, Source
from .records import EnvironmentLink, Market, Picture, Term
from .vocabulary import CURATOR, DOSSIER_SCHEMA_VERSION, CoverageClass

__all__ = [
    "DOSSIER_SCHEMA_TITLE",
    "Dossier",
    "dossier_json_schema",
    "dossier_schema_text",
    "parse_dossier",
]

DOSSIER_SCHEMA_TITLE = "KalaVigyan curated craft dossier"


class Dossier(ContractModel):
    schema_version: Literal[1] = DOSSIER_SCHEMA_VERSION
    craft_slug: str = Field(pattern=CRAFT_SLUG_PATTERN, max_length=200)
    version: int = Field(ge=1)
    curated_at: AwareDatetime
    curator: Literal["claude-code"] = CURATOR
    coverage: CoverageClass
    searched: list[Search] = Field(min_length=1)
    sources: list[Source] = Field(min_length=1)
    claims: list[Claim] = Field(min_length=1)
    places: list[Place] = Field(default_factory=list)
    communities: list[Community] = Field(default_factory=list)
    stages: list[Stage] = Field(default_factory=list)
    materials: list[Material] = Field(default_factory=list)
    tools: list[Tool] = Field(default_factory=list)
    reactions: list[Reaction] = Field(default_factory=list)
    environment: list[EnvironmentLink] = Field(default_factory=list)
    market: Market = Field(default_factory=Market)
    glossary: list[Term] = Field(default_factory=list)
    conflicts: list[Conflict] = Field(default_factory=list)
    open_questions: list[OpenQuestion] = Field(default_factory=list)
    pictures: list[Picture] = Field(default_factory=list, max_length=PICTURES_MAX)
    overview: Overview

    def claim(self, claim_id: str) -> Claim:
        return next(claim for claim in self.claims if claim.id == claim_id)

    def source(self, source_id: str) -> Source:
        return next(source for source in self.sources if source.id == source_id)


def parse_dossier(text: str) -> Dossier:
    return Dossier.model_validate_json(text)


def dossier_json_schema() -> dict[str, Any]:
    schema = Dossier.model_json_schema(by_alias=True)
    return {"$schema": "https://json-schema.org/draft/2020-12/schema", "title": DOSSIER_SCHEMA_TITLE} | {
        key: value for key, value in schema.items() if key != "title"
    }


def dossier_schema_text() -> str:
    return json.dumps(dossier_json_schema(), indent=2, ensure_ascii=False) + "\n"
