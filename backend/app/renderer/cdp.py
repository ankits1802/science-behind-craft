from __future__ import annotations

import asyncio
import itertools
import json
import logging
from collections.abc import Awaitable, Callable
from typing import Any, Protocol

__all__ = ["Cdp", "CdpError", "CdpSocket", "EventHandler", "Message"]

Message = dict[str, Any]
EventHandler = Callable[[Message, str | None], Awaitable[None]]

logger = logging.getLogger("kalavigyan.renderer")


class CdpError(Exception):
    pass


class CdpSocket(Protocol):
    async def send(self, message: str) -> None: ...

    async def recv(self) -> str | bytes: ...

    async def close(self) -> None: ...


class Cdp:
    def __init__(self, socket: CdpSocket) -> None:
        self._socket = socket
        self._ids = itertools.count(1)
        self._pending: dict[int, asyncio.Future[Message]] = {}
        self._waiting: list[tuple[str, str | None, asyncio.Future[Message]]] = []
        self._handlers: dict[str, EventHandler] = {}
        self._tasks: set[asyncio.Task[None]] = set()
        self._reader = asyncio.create_task(self._read())

    def on(self, method: str, handler: EventHandler) -> None:
        self._handlers[method] = handler

    def expect(self, method: str, session: str | None) -> asyncio.Future[Message]:
        future: asyncio.Future[Message] = asyncio.get_running_loop().create_future()
        self._waiting.append((method, session, future))
        return future

    async def send(
        self, method: str, params: Message | None = None, *, session: str | None = None
    ) -> Message:
        ident = next(self._ids)
        message: Message = {"id": ident, "method": method, "params": params or {}}
        if session is not None:
            message["sessionId"] = session
        future: asyncio.Future[Message] = asyncio.get_running_loop().create_future()
        self._pending[ident] = future
        await self._socket.send(json.dumps(message))
        return await future

    async def close(self) -> None:
        self._reader.cancel()
        for task in list(self._tasks):
            task.cancel()
        await self._socket.close()

    async def _read(self) -> None:
        try:
            while True:
                self._dispatch(json.loads(await self._socket.recv()))
        except Exception as closed:
            self._fail(CdpError(f"the browser's connection ended ({type(closed).__name__})"))

    def _dispatch(self, message: Message) -> None:
        ident = message.get("id")
        if isinstance(ident, int):
            self._answer(ident, message)
            return
        method, session = str(message.get("method")), message.get("sessionId")
        params: Message = message.get("params") or {}
        for entry in [entry for entry in self._waiting if entry[:2] == (method, session)]:
            self._waiting.remove(entry)
            if not entry[2].done():
                entry[2].set_result(params)
        handler = self._handlers.get(method)
        if handler is not None:
            task = asyncio.create_task(handler(params, session))
            self._tasks.add(task)
            task.add_done_callback(self._settled)

    def _answer(self, ident: int, message: Message) -> None:
        future = self._pending.pop(ident, None)
        if future is None or future.done():
            return
        error = message.get("error")
        if error is not None:
            future.set_exception(CdpError(str(error.get("message", error))))
        else:
            future.set_result(message.get("result") or {})

    def _settled(self, task: asyncio.Task[None]) -> None:
        self._tasks.discard(task)
        if not task.cancelled() and task.exception() is not None:
            logger.info("a browser event was not handled: %s", task.exception())

    def _fail(self, error: CdpError) -> None:
        for future in [*self._pending.values(), *(entry[2] for entry in self._waiting)]:
            if not future.done():
                future.set_exception(error)
        self._pending.clear()
        self._waiting.clear()
