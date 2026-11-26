from __future__ import annotations

from collections.abc import Awaitable, Mapping, Sequence
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from types import MappingProxyType
from typing import Any

from pydantic import BaseModel, ValidationError

from app.core.config import get_settings
from app.core.errors import InvalidInput, Refused

from .mcp_files import FileInput, file_problem, given_files, upload_required
from .mcp_input import Answer, Question, answers_to, input_required
from .mcp_protocol import INVALID_PARAMS, RequestError, tool_error, tool_result
from .mcp_state import (
    ASKED,
    ASKED_AFTER,
    UPLOADED,
    SealedCall,
    arguments_digest,
    opened_state,
    sealed_state,
)
from .mcp_tasks import task_reply
from .mcp_tool_base import Sessions, Tool, ToolContext, scope_refusal, shown_images

__all__ = ["ASKED_FOR", "UPLOAD_GRACE", "call_tool", "problems", "run_tool"]

ASKED_FOR = timedelta(hours=1)
UPLOAD_GRACE = timedelta(minutes=30)
TASK = "task"
ANOTHER_CALL = "requestState belongs to another call, tool or account; call the tool again without it"
NOT_ASKED = "requestState answers a form, and this client declares no form elicitation to answer it with"
RUNNING = "{title}: running"


async def call_tool(tool: Tool, params: Mapping[str, Any], context: ToolContext) -> dict[str, Any]:
    prepared = _prepared(tool, params, context)
    if isinstance(prepared, dict):
        return prepared
    arguments, files = prepared
    now = datetime.now(UTC)
    sealed = _opened(tool, params, context, now)
    if sealed is not None and sealed.purpose == ASKED_AFTER:
        return await _answered_after(tool, arguments, params, context, sealed)
    context = replace(context, files=tuple(files))
    if sealed is not None and sealed.purpose == UPLOADED:
        context = replace(context, uploaded=MappingProxyType(dict(sealed.refs)))
    elif files:
        return await _staged(tool, arguments, params, context)
    try:
        questions = await _questions(tool, arguments, context)
    except (InvalidInput, Refused) as refused:
        return tool_error(str(refused))
    if questions:
        answers = _answers(questions, params, sealed)
        if answers is None:
            keys = tuple(question.key for question in questions)
            state = _seal(tool, params, context, purpose=ASKED, expires=now + ASKED_FOR, keys=keys)
            return input_required(questions, state)
        context = replace(context, answers=answers)
    sessions = _task_sessions(tool, context, now)
    if sessions is not None:
        return await _task(tool, arguments, context, sessions, now)
    if tool.after is not None and _elicits(context):
        return await _asked_after(tool, arguments, params, context, now)
    return await run_tool(tool, arguments, context)


async def run_tool(tool: Tool, arguments: Any, context: ToolContext) -> dict[str, Any]:
    return _replied(await _ran(tool, tool.run(context, arguments), context))


def problems(refused: ValidationError) -> str:
    return "; ".join(
        f"{'.'.join(str(part) for part in problem['loc']) or 'arguments'}: {problem['msg']}"
        for problem in refused.errors()
    )


def _prepared(
    tool: Tool, params: Mapping[str, Any], context: ToolContext
) -> tuple[Any, list[FileInput]] | dict[str, Any]:
    given = params.get("arguments") or {}
    try:
        rest, files = (
            (given, [])
            if tool.files is None or not isinstance(given, Mapping)
            else given_files(given, tool.files)
        )
        arguments = tool.arguments.model_validate(rest)
    except ValidationError as refused:
        return tool_error(problems(refused))
    except ValueError as refused:
        return tool_error(str(refused))
    refusal = scope_refusal(tool, context, given)
    if refusal is not None:
        return tool_error(refusal)
    return arguments, files


def _opened(tool: Tool, params: Mapping[str, Any], context: ToolContext, now: datetime) -> SealedCall | None:
    state = params.get("requestState")
    if state is None:
        return None
    sealed = opened_state(state, now)
    if not sealed.matches(tool.name, params.get("arguments") or {}, context.principal):
        raise RequestError(INVALID_PARAMS, ANOTHER_CALL)
    return sealed


async def _questions(tool: Tool, arguments: Any, context: ToolContext) -> Sequence[Question]:
    if tool.asks is None or not _elicits(context):
        return ()
    return await tool.asks(context, arguments)


def _elicits(context: ToolContext) -> bool:
    return context.meta is not None and context.meta.elicits_forms()


async def _ran(tool: Tool, work: Awaitable[BaseModel], context: ToolContext) -> BaseModel | dict[str, Any]:
    try:
        reply = await work
    except (InvalidInput, Refused) as refused:
        if tool.commits:
            await context.session.rollback()
        return tool_error(str(refused))
    if tool.commits:
        await context.session.commit()
    return reply


def _replied(ran: BaseModel | dict[str, Any]) -> dict[str, Any]:
    if isinstance(ran, dict):
        return ran
    return tool_result(ran.model_dump(mode="json", by_alias=True), shown_images(ran))


async def _asked_after(
    tool: Tool, arguments: Any, params: Mapping[str, Any], context: ToolContext, now: datetime
) -> dict[str, Any]:
    ran = await _ran(tool, tool.run(context, arguments), context)
    follow = None if tool.after is None or isinstance(ran, dict) else await tool.after.ask(context, ran)
    if follow is None:
        return _replied(ran)
    keys = (follow.question.key,)
    expires = now + ASKED_FOR
    state = _seal(tool, params, context, purpose=ASKED_AFTER, expires=expires, keys=keys, refs=follow.refs)
    return input_required([follow.question], state)


async def _answered_after(
    tool: Tool, arguments: Any, params: Mapping[str, Any], context: ToolContext, sealed: SealedCall
) -> dict[str, Any]:
    if tool.after is None or not _elicits(context):
        raise RequestError(INVALID_PARAMS, NOT_ASKED)
    answers = MappingProxyType(answers_to(sealed.keys, params.get("inputResponses")))
    asked = replace(context, answers=answers)
    return _replied(await _ran(tool, tool.after.answered(asked, arguments, sealed.refs), asked))


def _answers(
    questions: Sequence[Question], params: Mapping[str, Any], sealed: SealedCall | None
) -> Mapping[str, Answer] | None:
    keys = tuple(question.key for question in questions)
    if sealed is None or sealed.purpose != ASKED or sealed.keys != keys:
        return None
    answers = answers_to(keys, params.get("inputResponses"))
    return MappingProxyType(answers) if len(answers) == len(keys) else None


async def _staged(
    tool: Tool, arguments: Any, params: Mapping[str, Any], context: ToolContext
) -> dict[str, Any]:
    argument = tool.files
    if argument is None:
        return await run_tool(tool, arguments, context)
    enabled = get_settings().mcp_file_uploads_enabled
    problem = file_problem(context.files, argument, context.meta, enabled=enabled)
    if problem is not None:
        return tool_error(problem)
    try:
        staged = await argument.stage(context, arguments)
    except (InvalidInput, Refused) as refused:
        await context.session.rollback()
        return tool_error(str(refused))
    await context.session.commit()
    refs = {item.file_id: item.ref for item in staged}
    expires = max(item.expires_at for item in staged) + UPLOAD_GRACE
    return upload_required(staged, _seal(tool, params, context, purpose=UPLOADED, expires=expires, refs=refs))


def _seal(
    tool: Tool,
    params: Mapping[str, Any],
    context: ToolContext,
    *,
    purpose: str,
    expires: datetime,
    keys: tuple[str, ...] = (),
    refs: Mapping[str, str] | None = None,
) -> str:
    call = SealedCall(
        tool=tool.name,
        arguments=arguments_digest(params.get("arguments") or {}),
        principal=context.principal,
        purpose=purpose,
        keys=keys,
        refs=dict(refs or {}),
        expires=int(expires.timestamp()),
    )
    return sealed_state(call)


def _task_sessions(tool: Tool, context: ToolContext, now: datetime) -> Sessions | None:
    meta, tasks, principal = context.meta, context.tasks, context.principal
    if not tool.runs_long or meta is None or not meta.runs_tasks() or tasks is None or principal is None:
        return None
    return context.sessions if tasks.has_room(principal, now) else None


async def _task(
    tool: Tool, arguments: Any, context: ToolContext, sessions: Sessions, now: datetime
) -> dict[str, Any]:
    tasks, principal = context.tasks, context.principal
    if tasks is None or principal is None:
        return await run_tool(tool, arguments, context)
    work = _in_background(tool, arguments, context, sessions)
    record = tasks.start(principal, work, said=RUNNING.format(title=tool.title), now=now)
    return task_reply(record, TASK)


async def _in_background(
    tool: Tool, arguments: Any, context: ToolContext, sessions: Sessions
) -> dict[str, Any]:
    async with sessions() as session:
        return await run_tool(tool, arguments, replace(context, session=session))
