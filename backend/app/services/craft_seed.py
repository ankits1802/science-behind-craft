import uuid
from collections.abc import Iterable
from typing import Any

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Craft, CraftAlias, CraftCategory, CraftCode, CraftSpelling, CraftSubCategory

BATCH = 500

CRAFT_COLUMNS = (
    "name",
    "subCategoryId",
    "category",
    "sourceSerial",
    "stateOfOrigin",
    "stateOfPractice",
    "giStatus",
    "isCatchAll",
    "sourceNotes",
    "craftCode",
)


def _chunks(rows: list[dict[str, Any]], size: int = BATCH) -> Iterable[list[dict[str, Any]]]:
    for start in range(0, len(rows), size):
        yield rows[start : start + size]


def _uuid(value: Any) -> uuid.UUID:
    return value if isinstance(value, uuid.UUID) else uuid.UUID(str(value))


async def _ids_by_slug(session: AsyncSession, model: Any) -> dict[str, uuid.UUID]:
    return dict((await session.execute(select(model.slug, model.id))).all())


async def seed_crafts(
    session: AsyncSession, plan: dict[str, list[dict[str, Any]]] | None = None
) -> dict[str, int]:
    if plan is None:
        from app.data.craft_master_loader import seed_plan

        plan = seed_plan()

    for row in plan["categories"]:
        values = {
            "id": _uuid(row["id"]),
            "slug": row["slug"],
            "name": row["name"],
            "sortOrder": row["sortOrder"],
        }
        await session.execute(
            insert(CraftCategory)
            .values(**values)
            .on_conflict_do_update(
                index_elements=[CraftCategory.slug],
                set_={"name": values["name"], "sortOrder": values["sortOrder"]},
            )
        )
    category_ids = await _ids_by_slug(session, CraftCategory)
    seed_category_slug = {_uuid(row["id"]): row["slug"] for row in plan["categories"]}

    for row in plan["subCategories"]:
        category_id = category_ids[seed_category_slug[_uuid(row["categoryId"])]]
        values = {
            "id": _uuid(row["id"]),
            "slug": row["slug"],
            "name": row["name"],
            "categoryId": category_id,
            "sortOrder": row["sortOrder"],
        }
        await session.execute(
            insert(CraftSubCategory)
            .values(**values)
            .on_conflict_do_update(
                index_elements=[CraftSubCategory.slug],
                set_={"name": values["name"], "categoryId": category_id, "sortOrder": values["sortOrder"]},
            )
        )
    sub_ids = await _ids_by_slug(session, CraftSubCategory)
    seed_sub_slug = {_uuid(row["id"]): row["slug"] for row in plan["subCategories"]}

    for chunk in _chunks(plan["codes"]):
        await session.execute(
            insert(CraftCode)
            .values([{"code": r["code"], "name": r["name"]} for r in chunk])
            .on_conflict_do_update(
                index_elements=[CraftCode.code], set_={"name": insert(CraftCode).excluded.name}
            )
        )
    for chunk in _chunks(plan["spellings"]):
        await session.execute(
            insert(CraftSpelling)
            .values(
                [
                    {
                        "spelling": r["spelling"],
                        "label": r["label"],
                        "craftCode": r["craftCode"],
                        "source": r["source"],
                    }
                    for r in chunk
                ]
            )
            .on_conflict_do_nothing(index_elements=[CraftSpelling.spelling])
        )

    existing = {
        slug: (row_id, meta)
        for slug, row_id, meta in (
            await session.execute(select(Craft.slug, Craft.id, Craft.extraMetadata))
        ).all()
    }
    seed_craft_slug: dict[uuid.UUID, str] = {}
    for row in plan["crafts"]:
        seed_craft_slug[_uuid(row["id"])] = row["slug"]
        values = {column: row.get(column) for column in CRAFT_COLUMNS}
        values["subCategoryId"] = sub_ids[seed_sub_slug[_uuid(row["subCategoryId"])]]
        found = existing.get(row["slug"])
        meta = dict(found[1] or {}) if found else {}
        meta.update(row.get("extraMetadata") or {})
        if row.get("masterId"):
            meta["masterId"] = row["masterId"]
        values["extraMetadata"] = meta
        if found is None:
            await session.execute(
                insert(Craft).values(
                    id=_uuid(row["id"]), slug=row["slug"], status=row.get("status", "ACTIVE"), **values
                )
            )
        else:
            await session.execute(
                insert(Craft)
                .values(id=found[0], slug=row["slug"], **values)
                .on_conflict_do_update(index_elements=[Craft.slug], set_=values)
            )
    craft_ids = await _ids_by_slug(session, Craft)

    alias_rows = []
    for row in plan["aliases"]:
        slug = seed_craft_slug.get(_uuid(row["craftId"]))
        if slug is None or slug not in craft_ids:
            continue
        alias_rows.append(
            {
                "craftId": craft_ids[slug],
                "alias": str(row["alias"])[:300],
                "aliasNorm": str(row["aliasNorm"])[:300],
                "script": row.get("script"),
                "lang": row.get("lang"),
                "source": row["source"],
                "status": row.get("status", "ACTIVE"),
            }
        )
    for chunk in _chunks(alias_rows):
        await session.execute(
            insert(CraftAlias)
            .values(chunk)
            .on_conflict_do_nothing(index_elements=[CraftAlias.craftId, CraftAlias.aliasNorm])
        )
    await session.flush()
    return {
        "categories": len(plan["categories"]),
        "subCategories": len(plan["subCategories"]),
        "crafts": len(plan["crafts"]),
        "codes": len(plan["codes"]),
        "spellings": len(plan["spellings"]),
        "aliases": len(alias_rows),
    }
