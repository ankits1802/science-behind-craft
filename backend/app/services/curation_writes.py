from __future__ import annotations

import uuid
from collections.abc import Collection, Sequence
from itertools import batched
from typing import Any

from sqlalchemy import ColumnElement, Table, bindparam, delete, func, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

__all__ = [
    "BATCH",
    "delete_rows",
    "insert_missing",
    "keep_only",
    "stored_values",
    "sync_rows",
    "update_rows",
]

BATCH = 500
UPDATED_AT = "updatedAt"
BOUND = "b_"


def _table(model: Any) -> Table:
    return model.__table__


def _unique(rows: Sequence[dict[str, Any]], key: str) -> list[dict[str, Any]]:
    seen: dict[Any, dict[str, Any]] = {}
    for row in rows:
        seen.setdefault(row[key], row)
    return list(seen.values())


async def stored_values(
    session: AsyncSession, model: Any, ids: Collection[Any], columns: Sequence[str], *, key: str = "id"
) -> dict[Any, dict[str, Any]]:
    table = _table(model)
    found: dict[Any, dict[str, Any]] = {}
    for chunk in batched(list(ids), BATCH, strict=False):
        statement = select(*(table.c[column] for column in dict.fromkeys([key, *columns])))
        for row in (await session.execute(statement.where(table.c[key].in_(chunk)))).mappings():
            found[row[key]] = dict(row)
    return found


async def sync_rows(
    session: AsyncSession, model: Any, rows: Sequence[dict[str, Any]], *, key: str = "id"
) -> int:
    planned = _unique(rows, key)
    if not planned:
        return 0
    columns = list(planned[0])
    current = await stored_values(session, model, [row[key] for row in planned], columns, key=key)
    inserts = [row for row in planned if row[key] not in current]
    updates = [
        row
        for row in planned
        if row[key] in current and any(current[row[key]][column] != row[column] for column in columns)
    ]
    for chunk in batched(inserts, BATCH, strict=False):
        await session.execute(insert(_table(model)).values(list(chunk)))
    await update_rows(session, model, updates, key=key)
    return len(inserts) + len(updates)


async def update_rows(
    session: AsyncSession, model: Any, rows: Sequence[dict[str, Any]], *, key: str = "id"
) -> None:
    if not rows:
        return
    table = _table(model)
    columns = [column for column in rows[0] if column != key]
    values: dict[str, Any] = {column: bindparam(f"{BOUND}{column}") for column in columns}
    if UPDATED_AT in table.c:
        values[UPDATED_AT] = func.now()
    statement = update(table).where(table.c[key] == bindparam(f"{BOUND}{key}")).values(values)
    params = [{f"{BOUND}{column}": row[column] for column in [key, *columns]} for row in rows]
    for chunk in batched(params, BATCH, strict=False):
        await session.execute(statement, list(chunk))


async def insert_missing(session: AsyncSession, model: Any, rows: Sequence[dict[str, Any]]) -> int:
    inserted = 0
    for chunk in batched(rows, BATCH, strict=False):
        statement = insert(_table(model)).values(list(chunk)).on_conflict_do_nothing()
        result = await session.execute(statement)
        inserted += max(result.rowcount or 0, 0)
    return inserted


async def delete_rows(session: AsyncSession, model: Any, *conditions: ColumnElement[bool]) -> int:
    result = await session.execute(delete(_table(model)).where(*conditions))
    return max(result.rowcount or 0, 0)


def keep_only(column: Any, kept: Collection[uuid.UUID]) -> ColumnElement[bool]:
    return column.not_in(list(kept)) if kept else column.is_not(None)
