from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any, Literal

from pydantic import ConfigDict, Field, ValidationError, model_validator

from app.core.errors import InvalidInput
from app.models.enums import CRAFT_STATUSES, GI_STATUSES
from app.research.base import ContractModel

__all__ = [
    "DESIGNER",
    "FEED_SCHEMA_VERSION",
    "FIELD_REPOSITORY",
    "PORTALS",
    "FeedCategory",
    "FeedCode",
    "FeedCraft",
    "FeedModel",
    "FeedSpelling",
    "FeedSubCategory",
    "Portal",
    "PortalCraftFeed",
    "first_problem",
    "parse_feed",
    "refuse_duplicates",
]

FEED_SCHEMA_VERSION = 1
DESIGNER = "DESIGNER"
FIELD_REPOSITORY = "FIELD_REPOSITORY"
PORTALS = (DESIGNER, FIELD_REPOSITORY)
MERGED = "MERGED"

Portal = Literal[*PORTALS]
CraftStatusValue = Literal[*CRAFT_STATUSES]
GiStatusValue = Literal[*GI_STATUSES]


class FeedModel(ContractModel):
    model_config = ConfigDict(extra="ignore")


class FeedSubCategory(FeedModel):
    id: str = Field(min_length=1, max_length=64)
    slug: str = Field(min_length=1, max_length=160)
    name: str = Field(min_length=1, max_length=200)
    sort_order: int = 0


class FeedCategory(FeedModel):
    id: str = Field(min_length=1, max_length=64)
    slug: str = Field(min_length=1, max_length=160)
    name: str = Field(min_length=1, max_length=200)
    sort_order: int = 0
    sub_categories: tuple[FeedSubCategory, ...] = ()


class FeedCraft(FeedModel):
    id: str = Field(min_length=1, max_length=64)
    slug: str = Field(min_length=1, max_length=200)
    name: str = Field(min_length=1, max_length=300)
    local_name: str | None = Field(default=None, max_length=300)
    sub_category_id: str | None = None
    state_of_origin: tuple[str, ...] = ()
    state_of_practice: tuple[str, ...] = ()
    gi_status: GiStatusValue | None = None
    is_catch_all: bool = False
    craft_code: str | None = Field(default=None, max_length=40)
    status: CraftStatusValue
    merged_into_id: str | None = None
    aliases: tuple[Annotated[str, Field(max_length=300)], ...] = ()
    updated_at: datetime | None = None

    @model_validator(mode="after")
    def _merge_needs_target(self) -> FeedCraft:
        if (self.status == MERGED) != (self.merged_into_id is not None):
            raise ValueError(f"craft {self.slug}: status MERGED and mergedIntoId must come together")
        return self


class FeedCode(FeedModel):
    code: str = Field(min_length=1, max_length=40)
    name: str = Field(min_length=1, max_length=200)


class FeedSpelling(FeedModel):
    spelling: str = Field(min_length=1, max_length=300)
    label: str = Field(min_length=1, max_length=300)
    craft_code: str = Field(min_length=1, max_length=40)
    source: str = Field(default="SHARED", min_length=1, max_length=40)


class PortalCraftFeed(FeedModel):
    schema_version: Literal[1]
    portal: Portal
    generated_at: datetime
    categories: tuple[FeedCategory, ...]
    crafts: tuple[FeedCraft, ...]
    codes: tuple[FeedCode, ...] = ()
    spellings: tuple[FeedSpelling, ...] = ()

    @model_validator(mode="after")
    def _references_resolve(self) -> PortalCraftFeed:
        refuse_duplicates("category slug", [c.slug for c in self.categories])
        subs = [s for c in self.categories for s in c.sub_categories]
        refuse_duplicates("sub-category id", [s.id for s in subs])
        refuse_duplicates("sub-category slug", [s.slug for s in subs])
        refuse_duplicates("craft id", [c.id for c in self.crafts])
        refuse_duplicates("craft slug", [c.slug for c in self.crafts])
        refuse_duplicates("code", [c.code for c in self.codes])
        sub_ids = {s.id for s in subs}
        craft_ids = {c.id for c in self.crafts}
        codes = {c.code for c in self.codes}
        for craft in self.crafts:
            _refuse_dangling(craft.slug, "subCategoryId", craft.sub_category_id, sub_ids)
            _refuse_dangling(craft.slug, "mergedIntoId", craft.merged_into_id, craft_ids)
            _refuse_dangling(craft.slug, "craftCode", craft.craft_code, codes)
            if craft.merged_into_id == craft.id:
                raise ValueError(f"craft {craft.slug} is merged into itself")
        for spelling in self.spellings:
            _refuse_dangling(spelling.spelling, "craftCode", spelling.craft_code, codes)
        return self


def parse_feed(payload: Any, *, portal: str) -> PortalCraftFeed:
    if not isinstance(payload, dict):
        raise InvalidInput(f"{portal} craft feed is not a JSON object")
    version = payload.get("schemaVersion")
    if version != FEED_SCHEMA_VERSION:
        raise InvalidInput(
            f"{portal} craft feed has schemaVersion {version!r}; this build reads {FEED_SCHEMA_VERSION}"
        )
    try:
        feed = PortalCraftFeed.model_validate(payload)
    except ValidationError as error:
        raise InvalidInput(f"{portal} craft feed breaks the contract: {first_problem(error)}") from None
    if feed.portal != portal:
        raise InvalidInput(f"the {portal} address answered with a feed from {feed.portal}")
    return feed


def refuse_duplicates(what: str, values: list[str]) -> None:
    seen: set[str] = set()
    for value in values:
        if value in seen:
            raise ValueError(f"{what} {value!r} appears twice")
        seen.add(value)


def first_problem(error: ValidationError) -> str:
    problem = error.errors()[0]
    where = ".".join(str(part) for part in problem.get("loc", ()))
    return f"{where} {problem.get('msg', '')}".strip()


def _refuse_dangling(owner: str, field: str, value: str | None, known: set[str]) -> None:
    if value is not None and value not in known:
        raise ValueError(f"{owner}: {field} {value!r} is not in the feed")
