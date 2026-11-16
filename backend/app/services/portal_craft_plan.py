from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from app.core.errors import InvalidInput
from app.data.craft_master_loader import ACTIVE, LEGACY, MERGED, normalise, seed_uuid
from app.services.portal_craft_feed import PORTALS, FeedCode, FeedCraft, FeedSpelling, PortalCraftFeed

__all__ = [
    "ORIGIN_KEY",
    "SOURCES_KEY",
    "CategoryWrite",
    "CraftColumns",
    "CraftWrite",
    "KnownCategory",
    "KnownCraft",
    "KnownState",
    "KnownSubCategory",
    "SubCategoryWrite",
    "TaxonomyPlan",
    "columns_of",
    "combined_status",
    "new_codes",
    "new_spellings",
    "ordered_feeds",
    "plan_taxonomy",
    "source_record",
]

SOURCES_KEY = "portalSources"
ORIGIN_KEY = "portalOrigin"


@dataclass(frozen=True)
class KnownCategory:
    slug: str
    name: str


@dataclass(frozen=True)
class KnownSubCategory:
    slug: str
    name: str
    category_slug: str


@dataclass(frozen=True)
class KnownCraft:
    slug: str
    name: str
    sub_category_slug: str | None
    status: str
    merged_into_slug: str | None
    meta: Mapping[str, Any]


@dataclass(frozen=True)
class KnownState:
    categories: tuple[KnownCategory, ...] = ()
    sub_categories: tuple[KnownSubCategory, ...] = ()
    crafts: tuple[KnownCraft, ...] = ()
    codes: frozenset[str] = frozenset()
    spellings: frozenset[str] = frozenset()
    master_slugs: frozenset[str] = frozenset()


@dataclass(frozen=True)
class CategoryWrite:
    id: str
    slug: str
    name: str
    sort_order: int


@dataclass(frozen=True)
class SubCategoryWrite:
    id: str
    slug: str
    name: str
    category_slug: str
    sort_order: int


@dataclass(frozen=True)
class CraftColumns:
    name: str
    local_name: str | None
    category: str | None
    sub_category_slug: str | None
    state_of_origin: tuple[str, ...]
    state_of_practice: tuple[str, ...]
    gi_status: str | None
    is_catch_all: bool
    craft_code: str | None


@dataclass(frozen=True)
class CraftWrite:
    id: str
    slug: str
    insert: bool
    columns: CraftColumns | None
    status: str | None
    merged_into_slug: str | None
    meta: Mapping[str, Any]


@dataclass
class TaxonomyPlan:
    categories: list[CategoryWrite] = field(default_factory=list)
    sub_categories: list[SubCategoryWrite] = field(default_factory=list)
    sub_slug_of: dict[tuple[str, str], str] = field(default_factory=dict)
    category_name_of_sub: dict[str, str] = field(default_factory=dict)


def ordered_feeds(feeds: Sequence[PortalCraftFeed]) -> list[PortalCraftFeed]:
    portals = [feed.portal for feed in feeds]
    repeated = sorted({portal for portal in portals if portals.count(portal) > 1})
    if repeated:
        raise InvalidInput(f"one craft feed per portal; got {', '.join(repeated)} more than once")
    return sorted(feeds, key=lambda feed: PORTALS.index(feed.portal))


def plan_taxonomy(feeds: Sequence[PortalCraftFeed], known: KnownState) -> TaxonomyPlan:
    plan = TaxonomyPlan()
    category_by_slug = {c.slug: c.name for c in known.categories}
    category_by_name = {normalise(c.name): c.slug for c in known.categories}
    sub_by_slug = {s.slug: s.category_slug for s in known.sub_categories}
    sub_by_name = {(s.category_slug, normalise(s.name)): s.slug for s in known.sub_categories}
    for feed in feeds:
        for category in feed.categories:
            kv_category = category.slug if category.slug in category_by_slug else None
            kv_category = kv_category or category_by_name.get(normalise(category.name))
            if kv_category is None:
                kv_category = category.slug
                plan.categories.append(
                    CategoryWrite(
                        seed_uuid("k", kv_category), kv_category, category.name, category.sort_order
                    )
                )
                category_by_slug[kv_category] = category.name
                category_by_name[normalise(category.name)] = kv_category
            for sub in category.sub_categories:
                kv_sub = (
                    sub.slug
                    if sub.slug in sub_by_slug
                    else sub_by_name.get((kv_category, normalise(sub.name)))
                )
                if kv_sub is None:
                    kv_sub = sub.slug
                    plan.sub_categories.append(
                        SubCategoryWrite(
                            seed_uuid("s", kv_sub), kv_sub, sub.name, kv_category, sub.sort_order
                        )
                    )
                    sub_by_slug[kv_sub] = kv_category
                    sub_by_name[(kv_category, normalise(sub.name))] = kv_sub
                plan.sub_slug_of[(feed.portal, sub.id)] = kv_sub
    plan.category_name_of_sub = {sub: category_by_slug[cat] for sub, cat in sub_by_slug.items()}
    return plan


def source_record(craft: FeedCraft, *, merged_into_slug: str | None, synced_at: str) -> dict[str, Any]:
    return {
        "id": craft.id,
        "slug": craft.slug,
        "name": craft.name,
        "status": craft.status,
        "mergedIntoSlug": merged_into_slug,
        "updatedAt": craft.updated_at.isoformat() if craft.updated_at else None,
        "syncedAt": synced_at,
    }


def combined_status(sources: Mapping[str, Mapping[str, Any]]) -> tuple[str, str | None]:
    listed = [sources[portal] for portal in PORTALS if portal in sources]
    if not listed:
        return LEGACY, None
    if any(_counts_as_active(record) for record in listed):
        return ACTIVE, None
    for record in listed:
        if record.get("status") == MERGED:
            return MERGED, record["mergedIntoSlug"]
    return LEGACY, None


def _counts_as_active(record: Mapping[str, Any]) -> bool:
    status = record.get("status")
    return status == ACTIVE or (status == MERGED and not record.get("mergedIntoSlug"))


def columns_of(craft: FeedCraft, *, sub_slug: str | None, category: str | None) -> CraftColumns:
    return CraftColumns(
        name=craft.name,
        local_name=craft.local_name,
        category=category,
        sub_category_slug=sub_slug,
        state_of_origin=craft.state_of_origin,
        state_of_practice=craft.state_of_practice,
        gi_status=craft.gi_status,
        is_catch_all=craft.is_catch_all,
        craft_code=craft.craft_code,
    )


def new_codes(feeds: Sequence[PortalCraftFeed], known: KnownState) -> list[FeedCode]:
    seen = set(known.codes)
    out: list[FeedCode] = []
    for feed in feeds:
        for code in feed.codes:
            if code.code not in seen:
                seen.add(code.code)
                out.append(code)
    return out


def new_spellings(feeds: Sequence[PortalCraftFeed], known: KnownState) -> list[FeedSpelling]:
    seen = set(known.spellings)
    out: list[FeedSpelling] = []
    for feed in feeds:
        for spelling in feed.spellings:
            if spelling.spelling not in seen:
                seen.add(spelling.spelling)
                out.append(spelling)
    return out
