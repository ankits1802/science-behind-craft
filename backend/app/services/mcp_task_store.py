from __future__ import annotations

import uuid
from collections.abc import AsyncIterator, Callable
from contextlib import AbstractAsyncContextManager, asynccontextmanager
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Protocol

from sqlalchemy import delete, func, select, update
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ExternalFailure
from app.models import McpTask
from app.models.oauth import MCP_TASK_STATUSES

__all__ = [
    "CANCELLED",
    "COMPLETED",
    "FAILED",
    "WORKING",
    "HeldTasks",
    "McpTasksReport",
    "SqlTaskStore",
    "TaskEnding",
    "TaskRecord",
    "TaskStore",
    "expired_task_count",
    "forget_expired_tasks",
]

WORKING, COMPLETED, FAILED, CANCELLED = MCP_TASK_STATUSES
STORE_DOWN = "The MCP task store could not be reached."

Sessions = Callable[[], AbstractAsyncContextManager[AsyncSession]]


@dataclass(frozen=True)
class TaskRecord:
    task_id: str
    principal: str
    tool: str
    arguments: str
    status_message: str
    created_at: datetime
    updated_at: datetime
    heartbeat_at: datetime
    expires_at: datetime
    status: str = WORKING
    result: dict[str, Any] | None = None
    error: dict[str, Any] | None = None

    def expired(self, now: datetime) -> bool:
        return self.expires_at <= now

    def silent_since(self, moment: datetime) -> bool:
        return self.status == WORKING and self.heartbeat_at <= moment


@dataclass(frozen=True)
class TaskEnding:
    status: str
    said: str
    result: dict[str, Any] | None = None
    error: dict[str, Any] | None = None


@dataclass(frozen=True)
class HeldTasks:
    mine: int
    everyone: int


class TaskStore(Protocol):
    async def add(self, record: TaskRecord) -> None: ...

    async def read(self, task_id: str) -> TaskRecord | None: ...

    async def end(self, task_id: str, ending: TaskEnding, *, now: datetime) -> bool: ...

    async def beat(self, task_id: str, *, now: datetime) -> bool: ...

    async def held(self, principal: str, *, now: datetime) -> HeldTasks: ...


@dataclass(frozen=True)
class SqlTaskStore:
    sessions: Sessions

    async def add(self, record: TaskRecord) -> None:
        async with self._session() as session:
            session.add(_row(record))

    async def read(self, task_id: str) -> TaskRecord | None:
        async with self._session() as session:
            row = await session.get(McpTask, task_id)
            return None if row is None else _record(row)

    async def end(self, task_id: str, ending: TaskEnding, *, now: datetime) -> bool:
        change = {
            "status": ending.status,
            "statusMessage": ending.said,
            "result": ending.result,
            "error": ending.error,
            "updatedAt": now,
        }
        return await self._working(task_id, change)

    async def beat(self, task_id: str, *, now: datetime) -> bool:
        return await self._working(task_id, {"heartbeatAt": now})

    async def held(self, principal: str, *, now: datetime) -> HeldTasks:
        mine = func.count().filter(McpTask.userId == uuid.UUID(principal))
        async with self._session() as session:
            counted = (await session.execute(select(mine, func.count()).where(McpTask.expiresAt > now))).one()
        return HeldTasks(mine=int(counted[0]), everyone=int(counted[1]))

    async def _working(self, task_id: str, change: dict[str, Any]) -> bool:
        async with self._session() as session:
            changed = await session.scalar(
                update(McpTask)
                .where(McpTask.id == task_id, McpTask.status == WORKING)
                .values(**change)
                .returning(McpTask.id)
            )
        return changed is not None

    @asynccontextmanager
    async def _session(self) -> AsyncIterator[AsyncSession]:
        try:
            async with self.sessions() as session:
                yield session
        except (SQLAlchemyError, OSError) as failed:
            raise ExternalFailure(STORE_DOWN, kind="unavailable", service="database") from failed


@dataclass
class McpTasksReport:
    expired_deleted: int = 0

    def as_dict(self) -> dict[str, Any]:
        return {"expiredDeleted": self.expired_deleted}


async def forget_expired_tasks(session: AsyncSession, *, now: datetime) -> McpTasksReport:
    removed = await session.scalars(delete(McpTask).where(McpTask.expiresAt <= now).returning(McpTask.id))
    report = McpTasksReport(expired_deleted=len(removed.all()))
    await session.commit()
    return report


async def expired_task_count(session: AsyncSession, *, now: datetime) -> int:
    return int(await session.scalar(select(func.count()).where(McpTask.expiresAt <= now)) or 0)


def _row(record: TaskRecord) -> McpTask:
    return McpTask(
        id=record.task_id,
        userId=uuid.UUID(record.principal),
        tool=record.tool,
        argumentsHash=record.arguments,
        status=record.status,
        statusMessage=record.status_message,
        result=record.result,
        error=record.error,
        createdAt=record.created_at,
        updatedAt=record.updated_at,
        heartbeatAt=record.heartbeat_at,
        expiresAt=record.expires_at,
    )


def _record(row: McpTask) -> TaskRecord:
    return TaskRecord(
        task_id=row.id,
        principal=str(row.userId),
        tool=row.tool,
        arguments=row.argumentsHash,
        status_message=row.statusMessage,
        created_at=row.createdAt,
        updated_at=row.updatedAt,
        heartbeat_at=row.heartbeatAt,
        expires_at=row.expiresAt,
        status=row.status,
        result=row.result,
        error=row.error,
    )
