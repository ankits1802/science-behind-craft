import asyncio
import json
import uuid
from dataclasses import replace
from datetime import UTC, datetime
from types import MappingProxyType
from typing import Any

import pytest
from pydantic import BaseModel

from app.api import mcp_tools
from app.api.mcp_tasks import TASKS_PER_PRINCIPAL
from app.api.mcp_tool_base import Arguments, Tool, ToolContext
from app.api.mcp_tools import LONG_RUNNING, TOOLS
from app.core.errors import InvalidInput
from app.models import User

from .modern_client import (
    FORMS,
    TASKS,
    bare_context,
    error_of,
    legacy,
    modern,
    result_of,
    tool_call,
    with_tasks,
)

PERSON = User(id=uuid.UUID(int=77), name="Meera Rao", email="meera@example.org", role="RESEARCHER")
OTHER = User(id=uuid.UUID(int=78), name="Asha Iyer", email="asha@example.org", role="RESEARCHER")
TASK_TTL_MS = 90 * 60 * 1000


class Echo(Arguments):
    text: str


class Echoed(BaseModel):
    text: str


def slow_tool(gate: asyncio.Event, *, fails: Exception | None = None) -> Tool:
    async def run(context: ToolContext, arguments: Echo) -> Echoed:
        await gate.wait()
        if fails is not None:
            raise fails
        return Echoed(text=arguments.text)

    return Tool(
        "slow_echo", "Echo slowly", "Echoes its text once the gate opens.", Echo, Echoed, run, runs_long=True
    )


@pytest.fixture
def gate(monkeypatch: pytest.MonkeyPatch) -> asyncio.Event:
    opened = asyncio.Event()
    monkeypatch.setattr(mcp_tools, "TOOLS", MappingProxyType({**TOOLS, "slow_echo": slow_tool(opened)}))
    return opened


def signed_in(user: User = PERSON) -> ToolContext:
    return with_tasks(bare_context(user=user, scopes=frozenset({"read", "contribute"})))


def echo_call(text: str = "indigo", *, capabilities: dict[str, Any] | None = None) -> dict[str, Any]:
    return modern(
        "tools/call",
        tool_call("slow_echo", {"text": text}),
        capabilities=TASKS if capabilities is None else capabilities,
    )


async def settled(context: ToolContext, task_id: str) -> None:
    assert context.tasks is not None and context.principal is not None
    runner = context.tasks.get(context.principal, task_id, datetime.now(UTC)).runner
    assert runner is not None
    await asyncio.wait({runner}, timeout=5)
    await asyncio.sleep(0)
    assert runner.done()


async def polled(context: ToolContext, task_id: str) -> dict[str, Any]:
    return await result_of(modern("tasks/get", {"taskId": task_id}, capabilities=TASKS), context)


def test_the_tools_that_can_take_more_than_a_few_seconds_run_as_tasks() -> None:
    assert {"preview_page", "compose_component", "read_source", "edit_draft", "propose_page"} <= LONG_RUNNING
    assert {name for name, tool in TOOLS.items() if tool.runs_long} == LONG_RUNNING
    assert not TOOLS["find_crafts"].runs_long and not TOOLS["get_facts"].runs_long


async def test_a_long_call_answers_with_a_task_whose_result_arrives_by_polling(gate: asyncio.Event) -> None:
    context = signed_in()
    created = await result_of(echo_call(), context)
    assert (created["resultType"], created["status"], created["pollIntervalMs"]) == ("task", "working", 2000)
    assert (
        created["ttlMs"] == TASK_TTL_MS
        and created["createdAt"].endswith("Z")
        and len(created["taskId"]) <= 128
    )
    task_id = created["taskId"]
    working = await polled(context, task_id)
    assert (working["resultType"], working["status"], working["taskId"]) == ("complete", "working", task_id)
    assert "result" not in working
    gate.set()
    await settled(context, task_id)
    done = await polled(context, task_id)
    assert done["status"] == "completed"
    assert done["result"]["structuredContent"] == {"text": "indigo"} and done["result"]["isError"] is False
    assert json.loads(done["result"]["content"][0]["text"]) == {"text": "indigo"}


@pytest.mark.parametrize(
    ("capabilities", "context"),
    [
        ({}, signed_in()),
        (FORMS, signed_in()),
        (TASKS, bare_context()),
        (TASKS, replace(signed_in(), tasks=None)),
    ],
)
async def test_a_client_without_tasks_gets_the_answer_itself(
    gate: asyncio.Event, capabilities: dict[str, Any], context: ToolContext
) -> None:
    gate.set()
    result = await result_of(echo_call(capabilities=capabilities), context)
    assert (result["resultType"], result["structuredContent"]) == ("complete", {"text": "indigo"})


async def test_an_old_protocol_client_gets_the_answer_itself(gate: asyncio.Event) -> None:
    gate.set()
    result = await result_of(legacy("tools/call", tool_call("slow_echo", {"text": "madder"})), signed_in())
    assert result["structuredContent"] == {"text": "madder"} and "resultType" not in result


async def test_a_task_is_read_only_by_its_own_account_and_only_by_a_client_that_runs_tasks(
    gate: asyncio.Event,
) -> None:
    context = signed_in()
    task_id = (await result_of(echo_call(), context))["taskId"]
    stranger = replace(context, user=OTHER)
    assert (await error_of(modern("tasks/get", {"taskId": task_id}, capabilities=TASKS), stranger))[
        "code"
    ] == -32602
    assert (await error_of(modern("tasks/get", {"taskId": "no-such-task"}, capabilities=TASKS), context))[
        "code"
    ] == -32602
    undeclared = await error_of(modern("tasks/get", {"taskId": task_id}), context)
    assert undeclared["code"] == -32021
    assert undeclared["data"]["requiredCapabilities"] == {"extensions": {"io.modelcontextprotocol/tasks": {}}}
    gate.set()
    await settled(context, task_id)


async def test_a_cancelled_task_says_so_and_an_update_is_acknowledged(gate: asyncio.Event) -> None:
    context = signed_in()
    task_id = (await result_of(echo_call(), context))["taskId"]
    updated = await result_of(
        modern("tasks/update", {"taskId": task_id, "inputResponses": {}}, capabilities=TASKS), context
    )
    assert updated["resultType"] == "complete"
    cancelled = await result_of(modern("tasks/cancel", {"taskId": task_id}, capabilities=TASKS), context)
    assert cancelled["resultType"] == "complete"
    await settled(context, task_id)
    assert (await polled(context, task_id))["status"] == "cancelled"


@pytest.mark.parametrize(
    ("failure", "status"),
    [(InvalidInput("The draft is gone."), "completed"), (RuntimeError("the renderer fell over"), "failed")],
)
async def test_a_refusal_completes_the_task_as_a_tool_error_and_a_crash_fails_it(
    monkeypatch: pytest.MonkeyPatch, failure: Exception, status: str
) -> None:
    opened = asyncio.Event()
    monkeypatch.setattr(
        mcp_tools, "TOOLS", MappingProxyType({**TOOLS, "slow_echo": slow_tool(opened, fails=failure)})
    )
    context = signed_in()
    task_id = (await result_of(echo_call(), context))["taskId"]
    opened.set()
    await settled(context, task_id)
    ended = await polled(context, task_id)
    assert ended["status"] == status
    if status == "completed":
        assert (
            ended["result"]["isError"] is True
            and ended["result"]["content"][0]["text"] == "The draft is gone."
        )
    else:
        assert ended["error"]["code"] == -32603 and "the renderer" not in ended["error"]["message"]


async def test_an_account_whose_tasks_are_all_held_gets_its_answer_itself(gate: asyncio.Event) -> None:
    context = signed_in()
    held = [(await result_of(echo_call(), context))["taskId"] for _ in range(TASKS_PER_PRINCIPAL)]
    gate.set()
    for task_id in held:
        await settled(context, task_id)
    answered = await result_of(echo_call("lime"), context)
    assert (answered["resultType"], answered["structuredContent"]) == ("complete", {"text": "lime"})
    other = await result_of(echo_call("alum"), replace(context, user=OTHER))
    assert other["resultType"] == "task"
    await settled(replace(context, user=OTHER), other["taskId"])
