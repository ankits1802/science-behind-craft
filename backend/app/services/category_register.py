from __future__ import annotations

import uuid
from collections.abc import Collection, Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.data.craft_families import CraftKind, load_craft_families
from app.data.craft_master_loader import ACTIVE, seed_plan, seed_uuid
from app.data.portal_craft_register import load_portal_crafts
from app.models import Craft, CraftCategory, CraftSubCategory, CuratedCraft

__all__ = [
    "CategoryRecord",
    "MemberRecord",
    "SubCategoryRecord",
    "category_records",
    "register_categories",
    "stored_categories",
]

GI = "GI"


@dataclass(frozen=True)
class MemberRecord:
    slug: str
    name: str
    gi_status: str | None
    catch_all: bool
    curated: bool


@dataclass(frozen=True)
class SubCategoryRecord:
    slug: str
    name: str
    label: str
    crafts: tuple[MemberRecord, ...]

    def craft_count(self) -> int:
        return sum(1 for craft in self.crafts if not craft.catch_all)


@dataclass(frozen=True)
class CategoryRecord:
    id: uuid.UUID
    slug: str
    name: str
    label: str
    palette: str | None
    sub_categories: tuple[SubCategoryRecord, ...]

    def craft_count(self) -> int:
        return sum(sub.craft_count() for sub in self.sub_categories)

    def member_slugs(self) -> set[str]:
        return {craft.slug for sub in self.sub_categories for craft in sub.crafts}


def category_records(
    categories: Sequence[Mapping[str, Any]],
    sub_categories: Sequence[Mapping[str, Any]],
    crafts: Sequence[Mapping[str, Any]],
) -> tuple[CategoryRecord, ...]:
    labels = load_craft_families()
    members: dict[str, list[MemberRecord]] = {}
    for craft in crafts:
        members.setdefault(str(craft["subCategoryId"]), []).append(_member(craft))
    ordered_subs = sorted(sub_categories, key=lambda sub: (sub["sortOrder"], sub["name"]))
    found = []
    for category in sorted(categories, key=lambda row: (row["sortOrder"], row["name"])):
        family = labels.family(category["slug"])
        subs = tuple(
            SubCategoryRecord(
                slug=sub["slug"],
                name=sub["name"],
                label=_kind_label(labels.kind(sub["slug"]), sub["name"]),
                crafts=tuple(sorted(members.get(str(sub["id"]), []), key=_member_order)),
            )
            for sub in ordered_subs
            if str(sub["categoryId"]) == str(category["id"])
        )
        label, palette = (family.label, family.palette) if family is not None else (category["name"], None)
        found.append(
            CategoryRecord(
                uuid.UUID(str(category["id"])), category["slug"], category["name"], label, palette, subs
            )
        )
    return tuple(found)


def _kind_label(kind: CraftKind | None, name: str) -> str:
    return kind.label if kind is not None else name


def _member(craft: Mapping[str, Any]) -> MemberRecord:
    return MemberRecord(
        slug=craft["slug"],
        name=craft["name"],
        gi_status=craft["giStatus"],
        catch_all=bool(craft["isCatchAll"]),
        curated=bool(craft["curated"]),
    )


def _member_order(craft: MemberRecord) -> tuple[bool, bool, bool, str, str]:
    return (craft.catch_all, not craft.curated, craft.gi_status != GI, craft.name.casefold(), craft.slug)


def register_categories(*, curated: Collection[str] = ()) -> tuple[CategoryRecord, ...]:
    plan = seed_plan()
    subs_by_slug = {sub["slug"]: sub for sub in plan["subCategories"]}
    crafts = [
        {**craft, "curated": craft["slug"] in curated}
        for craft in plan["crafts"]
        if craft["status"] == ACTIVE
    ]
    for portal in load_portal_crafts():
        sub = subs_by_slug.get(portal.sub_category_slug or "")
        if portal.status != ACTIVE or sub is None:
            continue
        crafts.append(
            {
                "id": seed_uuid("c", portal.slug),
                "slug": portal.slug,
                "name": portal.name,
                "subCategoryId": sub["id"],
                "giStatus": portal.gi_status,
                "isCatchAll": False,
                "curated": portal.slug in curated,
            }
        )
    return category_records(plan["categories"], plan["subCategories"], crafts)


async def stored_categories(session: AsyncSession, *, slug: str | None = None) -> tuple[CategoryRecord, ...]:
    chosen = select(CraftCategory.id, CraftCategory.slug, CraftCategory.name, CraftCategory.sortOrder)
    if slug is not None:
        chosen = chosen.where(CraftCategory.slug == slug)
    categories = [dict(row) for row in (await session.execute(chosen)).mappings()]
    if not categories:
        return ()
    subs = await session.execute(
        select(
            CraftSubCategory.id,
            CraftSubCategory.slug,
            CraftSubCategory.name,
            CraftSubCategory.categoryId,
            CraftSubCategory.sortOrder,
        ).where(CraftSubCategory.categoryId.in_([row["id"] for row in categories]))
    )
    sub_rows = [dict(row) for row in subs.mappings()]
    return category_records(
        categories, sub_rows, await _stored_members(session, [row["id"] for row in sub_rows])
    )


async def _stored_members(session: AsyncSession, sub_ids: Sequence[uuid.UUID]) -> list[dict[str, Any]]:
    if not sub_ids:
        return []
    curated = select(CuratedCraft.craftId).where(CuratedCraft.craftId == Craft.id).exists()
    rows = await session.execute(
        select(
            Craft.slug,
            Craft.name,
            Craft.subCategoryId,
            Craft.giStatus,
            Craft.isCatchAll,
            curated.label("curated"),
        ).where(Craft.subCategoryId.in_(list(sub_ids)), Craft.status == ACTIVE)
    )
    return [dict(row) for row in rows.mappings()]
