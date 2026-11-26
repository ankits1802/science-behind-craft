from __future__ import annotations

import asyncio
import logging
import secrets
from collections.abc import Coroutine, Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from functools import partial
from typing import Any

from .mcp_protocol import INTERNAL_ERROR, INVALID_PARAMS, RequestError

__all__ = [
    "POLL_INTERVAL_MS",
    "TASKS_PER_PRINCIPAL",
    "TASK_TTL",
    "UNKNOWN",
    "WORKING",
    "McpTasks",
    "TaskRecord",
    "task_reply",
]

logger = logging.getLogger(__name__)

WORKING, COMPLETED, FAILED, CANCELLED = "working", "completed", "failed", "cancelled"
TASK_TTL = timedelta(minutes=90)
POLL_INTERVAL_MS = 2000
TASKS_PER_PRINCIPAL = 32
TASKS_HELD = 2000
UNKNOWN = "Failed to retrieve task: no task of this connection has that id; it may have expired"
FAILED_MESSAGE = "The server failed while running the tool; call it again."
STOPPED = "The task was cancelled before it finished."

TaskWork = Coroutine[Any, Any, dict[str, Any]]


@dataclass
class TaskRecord:
    task_id: str
    principal: str
    status_message: str
    created_at: datetime
    updated_at: datetime
    status: str = WORKING
    result: dict[str, Any] | None = None
    error: dict[str, Any] | None = None
    runner: asyncio.Task[None] | None = field(default=None, repr=False)

    def expired(self, now: datetime) -> bool:
        return self.created_at + TASK_TTL <= now


class McpTasks:
    def __init__(self) -> None:
        self._held: dict[str, TaskRecord] = {}

    def has_room(self, principal: str, now: datetime) -> bool:
        self._forget_expired(now)
        mine = sum(record.principal == principal for record in self._held.values())
        return mine < TASKS_PER_PRINCIPAL and len(self._held) < TASKS_HELD

    def start(self, principal: str, work: TaskWork, *, said: str, now: datetime) -> TaskRecord:
        record = TaskRecord(
            task_id=secrets.token_urlsafe(24),
            principal=principal,
            status_message=said,
            created_at=now,
            updated_at=now,
        )
        self._held[record.task_id] = record
        record.runner = asyncio.create_task(self._run(record, work), name=f"mcp task {said}")
        record.runner.add_done_callback(partial(self._settled, record, work))
        return record

    def get(self, principal: str, task_id: Any, now: datetime) -> TaskRecord:
        self._forget_expired(now)
        record = self._held.get(task_id) if isinstance(task_id, str) else None
        if record is None or record.principal != principal:
            raise RequestError(INVALID_PARAMS, UNKNOWN)
        return record

    def cancel(self, principal: str, task_id: Any, now: datetime) -> TaskRecord:
        record = self.get(principal, task_id, now)
        if record.status == WORKING and record.runner is not None:
            record.runner.cancel()
        return record

    async def _run(self, record: TaskRecord, work: TaskWork) -> None:
        try:
            outcome = await work
        except asyncio.CancelledError:
            self._end(record, CANCELLED, said=STOPPED)
            return
        except Exception:
            logger.exception("an MCP task failed: %s", record.status_message)
            self._end(
                record, FAILED, said=FAILED_MESSAGE, error={"code": INTERNAL_ERROR, "message": FAILED_MESSAGE}
            )
            return
        self._end(record, COMPLETED, said=record.status_message, result=outcome)

    def _settled(self, record: TaskRecord, work: TaskWork, runner: asyncio.Task[None]) -> None:
        if runner.cancelled() and record.status == WORKING:
            work.close()
            self._end(record, CANCELLED, said=STOPPED)

    def _end(
        self,
        record: TaskRecord,
        status: str,
        *,
        said: str,
        result: dict[str, Any] | None = None,
        error: dict[str, Any] | None = None,
    ) -> None:
        record.status, record.status_message = status, said
        record.result, record.error = result, error
        record.updated_at = datetime.now(UTC)

    def _forget_expired(self, now: datetime) -> None:
        for task_id in [key for key, record in self._held.items() if record.expired(now)]:
            record = self._held.pop(task_id)
            if record.runner is not None and not record.runner.done():
                record.runner.cancel()


def task_reply(record: TaskRecord, result_type: str) -> dict[str, Any]:
    reply: dict[str, Any] = {
        "resultType": result_type,
        "taskId": record.task_id,
        "status": record.status,
        "statusMessage": record.status_message,
        "createdAt": _stamp(record.created_at),
        "lastUpdatedAt": _stamp(record.updated_at),
        "ttlMs": int(TASK_TTL.total_seconds() * 1000),
        "pollIntervalMs": POLL_INTERVAL_MS,
    }
    extra: Mapping[str, Any] = {}
    if record.status == COMPLETED and record.result is not None:
        extra = {"result": record.result}
    elif record.status == FAILED and record.error is not None:
        extra = {"error": record.error}
    return reply | dict(extra)


def _stamp(moment: datetime) -> str:
    return moment.astimezone(UTC).isoformat().replace("+00:00", "Z")
