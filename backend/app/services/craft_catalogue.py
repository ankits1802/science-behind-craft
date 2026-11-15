import hashlib
import uuid
from collections.abc import Iterable, Mapping
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.data.craft_master_loader import codes_normalise
from app.models import Craft, CraftAlias, CraftCategory, CraftSpelling, CraftSubCategory
from app.models.base import Base

ACTIVE = "ACTIVE"
UNPLACED = (10**6, 10**6, "")
REFERENCE_SKIP = frozenset({"Craft", "CraftAlias"})


def etag_matches(if_none_match: str | None, etag: str) -> bool:
    def bare(tag: str) -> str:
        tag = tag.strip()
        return tag[2:] if tag[:2].upper() == "W/" else tag

    tags = [bare(tag) for tag in (if_none_match or "").split(",") if tag.strip()]
    return "*" in tags or bare(etag) in tags


def quoted_etag(version: str) -> str:
    return f'"{version}"'


def _text(value: Any) -> str | None:
    return None if value is None else str(value)


def _stamp(value: Any) -> str:
    return value.isoformat() if hasattr(value, "isoformat") else str(value or "")


def _enum(value: Any) -> Any:
    return getattr(value, "value", value)


def _status(craft: Mapping[str, Any]) -> str:
    return str(_enum(craft.get("status")) or ACTIVE)


def assemble_catalogue(
    categories: Iterable[Mapping[str, Any]],
    sub_categories: Iterable[Mapping[str, Any]],
    crafts: Iterable[Mapping[str, Any]],
    spellings: Iterable[Mapping[str, Any]],
    aliases: Iterable[Mapping[str, Any]],
    *,
    include_inactive: bool = False,
    references: Mapping[str, int] | None = None,
) -> dict[str, Any]:
    category_rows = sorted(categories, key=lambda c: (c["sortOrder"], c["name"]))
    sub_rows = sorted(sub_categories, key=lambda s: (s["sortOrder"], s["name"]))
    craft_rows = [c for c in crafts if include_inactive or _status(c) == ACTIVE]
    spelling_rows = list(spellings)
    references = references or {}

    sub_order: dict[str, tuple[int, int, str]] = {}
    category_of: dict[str, str] = {}
    category_sort = {_text(c["id"]): c["sortOrder"] for c in category_rows}
    for sub in sub_rows:
        sub_id = _text(sub["id"]) or ""
        parent = _text(sub["categoryId"]) or ""
        category_of[sub_id] = parent
        sub_order[sub_id] = (category_sort.get(parent, 10**6), sub["sortOrder"], sub["name"])

    counts: dict[str, int] = {}
    for craft in craft_rows:
        sub_id = _text(craft.get("subCategoryId"))
        if sub_id and _status(craft) == ACTIVE:
            counts[sub_id] = counts.get(sub_id, 0) + 1

    category_payload = [
        {
            "id": _text(category["id"]),
            "slug": category["slug"],
            "name": category["name"],
            "sortOrder": category["sortOrder"],
            "subCategories": [
                {
                    "id": _text(sub["id"]),
                    "slug": sub["slug"],
                    "name": sub["name"],
                    "sortOrder": sub["sortOrder"],
                    "craftCount": counts.get(_text(sub["id"]) or "", 0),
                }
                for sub in sub_rows
                if _text(sub["categoryId"]) == _text(category["id"])
            ],
        }
        for category in category_rows
    ]

    def order(craft: Mapping[str, Any]) -> tuple[Any, ...]:
        serial = craft.get("sourceSerial")
        return (
            _status(craft) != ACTIVE,
            sub_order.get(_text(craft.get("subCategoryId")) or "", UNPLACED),
            serial is None,
            serial or 0,
            (craft.get("name") or "").lower(),
            _text(craft["id"]),
        )

    craft_rows.sort(key=order)

    by_code: dict[str, set[str]] = {}
    for row in spelling_rows:
        if row.get("craftCode"):
            by_code.setdefault(row["craftCode"], set()).add(row["spelling"])
    extra: dict[str, set[str]] = {}
    for row in aliases:
        if str(_enum(row.get("status")) or ACTIVE) == ACTIVE:
            extra.setdefault(_text(row["craftId"]) or "", set()).add(row["aliasNorm"])

    digest = hashlib.sha256()
    digest.update(b"inactive" if include_inactive else b"active")
    for category in category_rows:
        digest.update(f"k{category['id']}{category['name']}{_stamp(category.get('updatedAt'))}".encode())
    for sub in sub_rows:
        digest.update(f"s{sub['id']}{sub['categoryId']}{sub['name']}{_stamp(sub.get('updatedAt'))}".encode())
    for spelling, code in sorted((r["spelling"], r.get("craftCode") or "") for r in spelling_rows):
        digest.update(f"a{spelling}={code}".encode())

    rows: list[dict[str, Any]] = []
    for craft in craft_rows:
        craft_id = _text(craft["id"]) or ""
        names = set(by_code.get(craft.get("craftCode") or "", set())) | extra.get(craft_id, set())
        names.discard(codes_normalise(craft.get("name")))
        names.discard("")
        alias_list = sorted(names)
        digest.update(
            f"c{craft_id}{craft.get('name')}{_stamp(craft.get('updatedAt'))}{_status(craft)}{alias_list}".encode()
        )
        sub_id = _text(craft.get("subCategoryId"))
        row: dict[str, Any] = {
            "id": craft_id,
            "slug": craft.get("slug"),
            "name": craft.get("name"),
            "localName": craft.get("localName"),
            "categoryId": category_of.get(sub_id or "") or None,
            "subCategoryId": sub_id,
            "sourceSerial": craft.get("sourceSerial"),
            "stateOfOrigin": list(craft.get("stateOfOrigin") or []),
            "stateOfPractice": list(craft.get("stateOfPractice") or []),
            "giStatus": _enum(craft.get("giStatus")),
            "isCatchAll": bool(craft.get("isCatchAll")),
            "craftCode": craft.get("craftCode"),
            "aliases": alias_list,
        }
        if include_inactive:
            inactive = _status(craft) != ACTIVE
            row["status"] = _status(craft)
            row["mergedIntoId"] = _text(craft.get("mergedIntoId"))
            row["referenceCount"] = references.get(craft_id, 0) if inactive else None
        rows.append(row)
    return {"version": digest.hexdigest(), "categories": category_payload, "crafts": rows}


def _rows(result: Any) -> list[dict[str, Any]]:
    return [dict(row) for row in result.mappings().all()]


def reference_tables() -> list[Any]:
    return [
        table
        for name, table in sorted(Base.metadata.tables.items())
        if name not in REFERENCE_SKIP
        and "craftId" in table.c
        and any(fk.column.table.name == "Craft" for fk in table.c.craftId.foreign_keys)
    ]


async def reference_counts(session: AsyncSession, craft_ids: list[str]) -> dict[str, int]:
    counts: dict[str, int] = dict.fromkeys(craft_ids, 0)
    if not craft_ids:
        return counts
    for table in reference_tables():
        column = table.c.craftId
        result = await session.execute(
            select(column, func.count()).where(column.in_([uuid.UUID(i) for i in craft_ids])).group_by(column)
        )
        for craft_id, count in result.all():
            key = str(craft_id)
            if key in counts:
                counts[key] += int(count)
    return counts


async def load_catalogue(session: AsyncSession, *, include_inactive: bool = False) -> dict[str, Any]:
    craft_query = select(
        Craft.id,
        Craft.slug,
        Craft.name,
        Craft.localName,
        Craft.subCategoryId,
        Craft.sourceSerial,
        Craft.stateOfOrigin,
        Craft.stateOfPractice,
        Craft.giStatus,
        Craft.isCatchAll,
        Craft.craftCode,
        Craft.status,
        Craft.mergedIntoId,
        Craft.updatedAt,
    )
    if not include_inactive:
        craft_query = craft_query.where(Craft.status == ACTIVE)
    categories = _rows(
        await session.execute(
            select(
                CraftCategory.id,
                CraftCategory.slug,
                CraftCategory.name,
                CraftCategory.sortOrder,
                CraftCategory.updatedAt,
            )
        )
    )
    subs = _rows(
        await session.execute(
            select(
                CraftSubCategory.id,
                CraftSubCategory.slug,
                CraftSubCategory.name,
                CraftSubCategory.categoryId,
                CraftSubCategory.sortOrder,
                CraftSubCategory.updatedAt,
            )
        )
    )
    crafts = _rows(await session.execute(craft_query))
    spellings = _rows(await session.execute(select(CraftSpelling.spelling, CraftSpelling.craftCode)))
    aliases = _rows(
        await session.execute(
            select(CraftAlias.craftId, CraftAlias.aliasNorm, CraftAlias.status).where(
                CraftAlias.status == ACTIVE
            )
        )
    )
    references: dict[str, int] = {}
    if include_inactive:
        inactive = [str(c["id"]) for c in crafts if _status(c) != ACTIVE]
        references = await reference_counts(session, inactive)
    return assemble_catalogue(
        categories,
        subs,
        crafts,
        spellings,
        aliases,
        include_inactive=include_inactive,
        references=references,
    )
