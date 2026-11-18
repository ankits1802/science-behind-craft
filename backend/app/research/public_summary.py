from __future__ import annotations

from typing import Literal, Self

from pydantic import Field, model_validator

from .base import ContractModel
from .citations import AnswerSentence, SourceRef, cited_source_ids
from .craft_catalogue import CatalogueSummary
from .craft_page_context import HeroImage
from .crafts import CraftRef

__all__ = [
    "FEATURED_CRAFTS_MAX",
    "PUBLIC_SUMMARY_SCHEMA_VERSION",
    "FeaturedCraft",
    "PlacedPoint",
    "PublicSummary",
    "Specimen",
]

PUBLIC_SUMMARY_SCHEMA_VERSION = 1
FEATURED_CRAFTS_MAX = 3


class FeaturedCraft(ContractModel):
    craft: CraftRef
    local_name: str | None
    hero: HeroImage | None
    lede: AnswerSentence


class Specimen(ContractModel):
    craft: CraftRef
    sentence: AnswerSentence


class PlacedPoint(ContractModel):
    key: str = Field(min_length=1)
    name: str = Field(min_length=1)
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    total: int = Field(ge=1)
    curated: list[CraftRef]


class PublicSummary(ContractModel):
    schema_version: Literal[1]
    counts: CatalogueSummary
    featured: list[FeaturedCraft] = Field(max_length=FEATURED_CRAFTS_MAX)
    specimen: Specimen | None
    sources: list[SourceRef]
    points: list[PlacedPoint]

    @model_validator(mode="after")
    def _every_cited_source_listed_once(self) -> Self:
        sentences = [featured.lede for featured in self.featured]
        if self.specimen is not None:
            sentences.append(self.specimen.sentence)
        listed = [source.id for source in self.sources]
        if listed != cited_source_ids(sentences):
            raise ValueError("sources are the cited sources, once each, in the order first cited")
        if len({featured.craft.slug for featured in self.featured}) != len(self.featured):
            raise ValueError("each featured craft is listed once")
        if len({point.key for point in self.points}) != len(self.points):
            raise ValueError("each placed point is listed once")
        return self
