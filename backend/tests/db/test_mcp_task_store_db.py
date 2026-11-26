import asyncio
import uuid
from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from sqlalchemy import delete, select

from app.api.mcp_tasks import McpTasks, TaskCall
from app.core.db import session_scope
from app.models import McpTask, User
from app.services.mcp_task_store import (
    COMPLETED,
    FAILED,
    WORKING,
    SqlTaskStore,
    TaskEnding,
    TaskRecord,
    expired_task_count,
    forget_expired_tasks,
)

pytestmark = pytest.mark.db

NOW = datetime.now(UTC).replace(microsecond=0)
DIGEST = "a" * 64
RESULT = {
    "content": [{"type": "text", "text": "{}"}],
    "structuredContent": {"text": "indigo"},
    "isError": False,
}
CALL = TaskCall(tool="preview_page", arguments=DIGEST, said="Preview the page: running")
SERVER_STOPPED = (
    "The server restarted or stopped while this task ran, so it never finished; call the tool again."
)


@pytest.fixture
async def people() -> AsyncIterator[tuple[str, str]]:
    made = [
        User(id=uuid.uuid4(), name=name, email=f"{uuid.uuid4().hex[:10]}@example.org", role="RESEARCHER")
        for name in ("Meera Rao", "Asha Iyer")
    ]
    async with session_scope() as session:
        session.add_all(made)
    yield str(made[0].id), str(made[1].id)
    async with session_scope() as session:
        await session.execute(delete(User).where(User.id.in_([person.id for person in made])))


def record(principal: str, *, created: datetime = NOW) -> TaskRecord:
    return TaskRecord(
        task_id=uuid.uuid4().hex,
        principal=principal,
        tool="preview_page",
        arguments=DIGEST,
        status_message="Preview the page: running",
        created_at=created,
        updated_at=created,
        heartbeat_at=created,
        expires_at=created + timedelta(minutes=90),
    )


async def test_a_stored_task_reads_back_whole_and_ends_once(people: tuple[str, str]) -> None:
    store = SqlTaskStore(session_scope)
    mine, _ = people
    added = record(mine)
    await store.add(added)
    assert await store.read(added.task_id) == added
    assert await store.read("no-such-task") is None
    assert await store.beat(added.task_id, now=NOW + timedelta(seconds=30)) is True
    ending = TaskEnding(COMPLETED, "Preview the page: running", result=RESULT)
    assert await store.end(added.task_id, ending, now=NOW + timedelta(minutes=1)) is True
    late = TaskEnding(FAILED, "late", error={"code": -32603, "message": "late"})
    assert await store.end(added.task_id, late, now=NOW + timedelta(minutes=2)) is False
    assert await store.beat(added.task_id, now=NOW + timedelta(minutes=3)) is False
    ended = await store.read(added.task_id)
    assert ended is not None
    assert (ended.status, ended.result, ended.error) == (COMPLETED, RESULT, None)
    assert (ended.heartbeat_at, ended.updated_at) == (NOW + timedelta(seconds=30), NOW + timedelta(minutes=1))


async def test_an_account_s_live_tasks_are_counted_apart_from_everyone_s_and_expired_ones_are_not(
    people: tuple[str, str],
) -> None:
    store = SqlTaskStore(session_scope)
    mine, theirs = people
    before = await store.held(mine, now=NOW)
    for added in (record(mine), record(mine), record(theirs), record(mine, created=NOW - timedelta(hours=2))):
        await store.add(added)
    held = await store.held(mine, now=NOW)
    assert (held.mine - before.mine, held.everyone - before.everyone) == (2, 3)


async def test_the_nightly_upkeep_deletes_only_expired_tasks(people: tuple[str, str]) -> None:
    store = SqlTaskStore(session_scope)
    mine, _ = people
    live, old = record(mine), record(mine, created=NOW - timedelta(hours=2))
    await store.add(live)
    await store.add(old)
    async with session_scope() as session:
        assert await expired_task_count(session, now=NOW) >= 1
        report = await forget_expired_tasks(session, now=NOW)
        assert report.expired_deleted >= 1 and report.as_dict()["expiredDeleted"] == report.expired_deleted
        kept = set(
            await session.scalars(select(McpTask.id).where(McpTask.id.in_([live.task_id, old.task_id])))
        )
    assert kept == {live.task_id}
    assert await store.read(old.task_id) is None


async def test_a_finished_task_survives_a_restart_and_a_running_one_is_failed_when_its_process_closes(
    people: tuple[str, str],
) -> None:
    store = SqlTaskStore(session_scope)
    mine, _ = people
    gate = asyncio.Event()

    async def quick() -> dict[str, Any]:
        return RESULT

    async def waiting() -> dict[str, Any]:
        await gate.wait()
        return RESULT

    first = McpTasks(store)
    done = await first.start(mine, quick(), call=CALL, now=datetime.now(UTC))
    running = await first.start(mine, waiting(), call=CALL, now=datetime.now(UTC))
    runner = first.running(done.task_id)
    assert runner is not None
    await asyncio.wait({runner}, timeout=10)
    await first.close()
    later = McpTasks(store)
    found = await later.get(mine, done.task_id, datetime.now(UTC))
    assert (found.status, found.result, found.tool, found.arguments) == (COMPLETED, RESULT, CALL.tool, DIGEST)
    lost = await later.get(mine, running.task_id, datetime.now(UTC))
    assert (lost.status, lost.status_message) == (FAILED, SERVER_STOPPED)
    assert lost.error == {"code": -32603, "message": SERVER_STOPPED}


async def test_a_task_left_working_by_a_killed_process_is_failed_after_its_heartbeat_falls_silent(
    people: tuple[str, str],
) -> None:
    store = SqlTaskStore(session_scope)
    mine, _ = people
    now = datetime.now(UTC)
    orphan, fresh = record(mine, created=now - timedelta(minutes=10)), record(mine, created=now)
    await store.add(orphan)
    await store.add(fresh)
    later = McpTasks(store)
    assert (await later.get(mine, fresh.task_id, datetime.now(UTC))).status == WORKING
    failed = await later.get(mine, orphan.task_id, datetime.now(UTC))
    assert (failed.status, failed.status_message) == (FAILED, SERVER_STOPPED)
