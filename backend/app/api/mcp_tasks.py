from __future__ import annotations

import asyncio
import logging
import secrets
from collections.abc import Coroutine, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from functools import partial
from typing import Any

from app.core.errors import ExternalFailure
from app.services.mcp_task_store import (
    CANCELLED,
    COMPLETED,
    FAILED,
    WORKING,
    TaskEnding,
    TaskRecord,
    TaskStore,
)

from .mcp_protocol import INTERNAL_ERROR, INVALID_PARAMS, RequestError

__all__ = [
    "BEAT",
    "POLL_INTERVAL_MS",
    "SILENT",
    "TASKS_PER_PRINCIPAL",
    "TASK_TTL",
    "UNKNOWN",
    "WORKING",
    "McpTasks",
    "TaskCall",
    "TaskRecord",
    "task_reply",
]

logger = logging.getLogger(__name__)

TASK_TTL = timedelta(minutes=90)
POLL_INTERVAL_MS = 2000
TASKS_PER_PRINCIPAL = 32
TASKS_HELD = 2000
BEAT = timedelta(seconds=30)
SILENT = timedelta(minutes=2)
CLOSE_SECONDS = 5.0
UNKNOWN = "Failed to retrieve task: no task of this connection has that id; it may have expired"
FAILED_MESSAGE = "The server failed while running the tool; call it again."
STOPPED = "The task was cancelled before it finished."
SERVER_STOPPED = (
    "The server restarted or stopped while this task ran, so it never finished; call the tool again."
)
CRASHED = TaskEnding(FAILED, FAILED_MESSAGE, error={"code": INTERNAL_ERROR, "message": FAILED_MESSAGE})
LOST = TaskEnding(FAILED, SERVER_STOPPED, error={"code": INTERNAL_ERROR, "message": SERVER_STOPPED})
HALTED = TaskEnding(CANCELLED, STOPPED)

TaskWork = Coroutine[Any, Any, dict[str, Any]]


@dataclass(frozen=True)
class TaskCall:
    tool: str
    arguments: str
    said: str


@dataclass(frozen=True)
class Running:
    runner: asyncio.Task[None]
    expires_at: datetime


class McpTasks:
    def __init__(self, store: TaskStore) -> None:
        self._store = store
        self._running: dict[str, Running] = {}

    async def has_room(self, principal: str, now: datetime) -> bool:
        self._stop_expired(now)
        held = await self._store.held(principal, now=now)
        return held.mine < TASKS_PER_PRINCIPAL and held.everyone < TASKS_HELD

    async def start(self, principal: str, work: TaskWork, *, call: TaskCall, now: datetime) -> TaskRecord:
        record = TaskRecord(
            task_id=secrets.token_urlsafe(24),
            principal=principal,
            tool=call.tool,
            arguments=call.arguments,
            status_message=call.said,
            created_at=now,
            updated_at=now,
            heartbeat_at=now,
            expires_at=now + TASK_TTL,
        )
        try:
            await self._store.add(record)
        except BaseException:
            work.close()
            raise
        runner = asyncio.create_task(self._run(record, work), name=f"mcp task {call.said}")
        self._running[record.task_id] = Running(runner, record.expires_at)
        runner.add_done_callback(partial(self._settled, record.task_id, work))
        return record

    async def get(self, principal: str, task_id: Any, now: datetime) -> TaskRecord:
        self._stop_expired(now)
        record = await self._store.read(task_id) if isinstance(task_id, str) else None
        if record is None or record.principal != principal or record.expired(now):
            raise RequestError(INVALID_PARAMS, UNKNOWN)
        if task_id in self._running or not record.silent_since(now - SILENT):
            return record
        await self._store.end(task_id, LOST, now=now)
        settled = await self._store.read(task_id)
        if settled is None:
            raise RequestError(INVALID_PARAMS, UNKNOWN)
        return settled

    async def cancel(self, principal: str, task_id: Any, now: datetime) -> TaskRecord:
        record = await self.get(principal, task_id, now)
        if record.status != WORKING:
            return record
        await self._store.end(record.task_id, HALTED, now=now)
        running = self._running.get(record.task_id)
        if running is not None:
            running.runner.cancel()
        return record

    def running(self, task_id: str) -> asyncio.Task[None] | None:
        running = self._running.get(task_id)
        return None if running is None else running.runner

    async def close(self) -> None:
        runners = []
        for task_id, running in list(self._running.items()):
            await self._ended(task_id, LOST)
            running.runner.cancel()
            runners.append(running.runner)
        if runners:
            await asyncio.wait(runners, timeout=CLOSE_SECONDS)

    async def _run(self, record: TaskRecord, work: TaskWork) -> None:
        beating = asyncio.create_task(self._beat(record.task_id, asyncio.current_task()))
        try:
            outcome = await work
        except asyncio.CancelledError:
            await self._ended(record.task_id, HALTED)
            return
        except Exception:
            logger.exception("an MCP task failed: %s", record.status_message)
            await self._ended(record.task_id, CRASHED)
            return
        finally:
            beating.cancel()
        await self._ended(record.task_id, TaskEnding(COMPLETED, record.status_message, result=outcome))

    async def _beat(self, task_id: str, runner: asyncio.Task[Any] | None) -> None:
        while True:
            await asyncio.sleep(BEAT.total_seconds())
            try:
                working = await self._store.beat(task_id, now=datetime.now(UTC))
            except ExternalFailure:
                logger.warning("an MCP task's heartbeat could not be stored: %s", task_id)
                continue
            if not working and runner is not None:
                runner.cancel()
                return

    async def _ended(self, task_id: str, ending: TaskEnding) -> None:
        try:
            await self._store.end(task_id, ending, now=datetime.now(UTC))
        except ExternalFailure:
            logger.exception("an MCP task's end could not be stored: %s", task_id)

    def _settled(self, task_id: str, work: TaskWork, runner: asyncio.Task[None]) -> None:
        self._running.pop(task_id, None)
        if runner.cancelled():
            work.close()

    def _stop_expired(self, now: datetime) -> None:
        for running in list(self._running.values()):
            if running.expires_at <= now and not running.runner.done():
                running.runner.cancel()


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
