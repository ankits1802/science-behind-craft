import asyncio
from dataclasses import replace
from datetime import UTC, datetime, timedelta

import pytest

from app.api import mcp_tasks
from app.api.mcp_protocol import RequestError
from app.api.mcp_tasks import McpTasks
from app.api.mcp_tool_base import ToolContext

from .modern_client import TASKS, error_of, modern
from .task_stores import HeldTaskStore
from .test_mcp_tasks import OTHER, echo_call, gate, polled, result_of, settled, signed_in

__all__ = ["gate"]

SERVER_STOPPED = (
    "The server restarted or stopped while this task ran, so it never finished; call the tool again."
)


def on(store: HeldTaskStore) -> ToolContext:
    return replace(signed_in(), tasks=McpTasks(store))


def restarted(context: ToolContext, store: HeldTaskStore) -> ToolContext:
    return replace(context, tasks=McpTasks(store))


async def test_a_task_that_finished_before_a_deploy_is_read_by_the_next_process(gate: asyncio.Event) -> None:
    store = HeldTaskStore()
    first = on(store)
    task_id = (await result_of(echo_call("indigo"), first))["taskId"]
    gate.set()
    await settled(first, task_id)
    done = await polled(restarted(first, store), task_id)
    assert (done["status"], done["taskId"]) == ("completed", task_id)
    assert done["result"]["structuredContent"] == {"text": "indigo"}
    record = store.records[task_id]
    assert (record.tool, record.principal, len(record.arguments)) == (
        "slow_echo",
        str(signed_in().principal),
        64,
    )


async def test_a_task_still_running_when_its_process_stops_is_failed_with_a_reason_to_call_again(
    gate: asyncio.Event,
) -> None:
    store = HeldTaskStore()
    first = on(store)
    task_id = (await result_of(echo_call(), first))["taskId"]
    assert first.tasks is not None
    runner = first.tasks.running(task_id)
    await first.tasks.close()
    assert runner is not None and runner.done()
    failed = await polled(restarted(first, store), task_id)
    assert (failed["status"], failed["statusMessage"]) == ("failed", SERVER_STOPPED)
    assert failed["error"] == {"code": -32603, "message": SERVER_STOPPED}
    assert "result" not in failed


async def test_a_task_whose_process_died_fails_once_its_heartbeat_falls_silent_and_not_before(
    gate: asyncio.Event,
) -> None:
    store = HeldTaskStore()
    first = on(store)
    task_id = (await result_of(echo_call(), first))["taskId"]
    later = restarted(first, store)
    assert later.tasks is not None and later.principal is not None
    started = store.records[task_id].created_at
    beating = await later.tasks.get(later.principal, task_id, started + timedelta(seconds=90))
    assert beating.status == "working"
    silent = await later.tasks.get(later.principal, task_id, started + timedelta(minutes=3))
    assert (silent.status, silent.status_message) == ("failed", SERVER_STOPPED)
    gate.set()
    await settled(first, task_id)
    assert store.records[task_id].status == "failed"


async def test_the_process_running_a_task_keeps_it_working_however_late_its_heartbeat(
    gate: asyncio.Event,
) -> None:
    first = on(HeldTaskStore())
    task_id = (await result_of(echo_call(), first))["taskId"]
    assert first.tasks is not None and first.principal is not None
    late = datetime.now(UTC) + timedelta(minutes=30)
    assert (await first.tasks.get(first.principal, task_id, late)).status == "working"
    gate.set()
    await settled(first, task_id)


async def test_a_heartbeat_keeps_a_task_alive_and_a_cancel_from_another_process_stops_its_runner(
    gate: asyncio.Event, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(mcp_tasks, "BEAT", timedelta(milliseconds=5))
    store = HeldTaskStore()
    first = on(store)
    task_id = (await result_of(echo_call(), first))["taskId"]
    while not store.beats:
        await asyncio.sleep(0.005)
    assert store.records[task_id].heartbeat_at > store.records[task_id].created_at
    other = restarted(first, store)
    cancelled = await result_of(modern("tasks/cancel", {"taskId": task_id}, capabilities=TASKS), other)
    assert cancelled["resultType"] == "complete"
    await settled(first, task_id)
    stopped = await polled(other, task_id)
    assert (stopped["status"], stopped["statusMessage"]) == (
        "cancelled",
        "The task was cancelled before it finished.",
    )


async def test_tasks_held_by_an_earlier_process_count_against_the_account_and_stay_its_own(
    gate: asyncio.Event,
) -> None:
    store = HeldTaskStore()
    first = on(store)
    task_id = (await result_of(echo_call(), first))["taskId"]
    later = restarted(first, store)
    assert later.tasks is not None and later.principal is not None
    held = await store.held(later.principal, now=datetime.now(UTC))
    assert (held.mine, held.everyone) == (1, 1)
    stranger = replace(later, user=OTHER)
    refused = await error_of(modern("tasks/get", {"taskId": task_id}, capabilities=TASKS), stranger)
    assert refused["code"] == -32602
    gate.set()
    await settled(first, task_id)


async def test_an_expired_task_is_unknown_to_the_next_process(gate: asyncio.Event) -> None:
    store = HeldTaskStore()
    first = on(store)
    task_id = (await result_of(echo_call(), first))["taskId"]
    gate.set()
    await settled(first, task_id)
    later = restarted(first, store)
    assert later.tasks is not None and later.principal is not None
    gone = store.records[task_id].expires_at
    with pytest.raises(RequestError, match="no task of this connection has that id") as unknown:
        await later.tasks.get(later.principal, task_id, gone)
    assert unknown.value.code == -32602
