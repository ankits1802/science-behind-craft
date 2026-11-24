import asyncio
import json
from typing import Any

import pytest

from app.renderer.cdp import Cdp, CdpError


class FakeSocket:
    def __init__(self) -> None:
        self.sent: list[dict[str, Any]] = []
        self.incoming: asyncio.Queue[str | Exception] = asyncio.Queue()
        self.closed = False

    async def send(self, message: str) -> None:
        self.sent.append(json.loads(message))

    async def recv(self) -> str:
        item = await self.incoming.get()
        if isinstance(item, Exception):
            raise item
        return item

    async def close(self) -> None:
        self.closed = True

    def say(self, message: dict[str, Any]) -> None:
        self.incoming.put_nowait(json.dumps(message))


async def settled() -> None:
    for _ in range(5):
        await asyncio.sleep(0)


async def test_a_command_gets_its_own_answer_while_an_event_reaches_its_handler() -> None:
    socket = FakeSocket()
    cdp = Cdp(socket)
    seen: list[tuple[dict[str, Any], str | None]] = []

    async def paused(params: dict[str, Any], session: str | None) -> None:
        seen.append((params, session))

    cdp.on("Fetch.requestPaused", paused)
    call = asyncio.create_task(cdp.send("Page.navigate", {"url": "https://kalavigyan.example"}, session="S1"))
    await settled()
    assert socket.sent == [
        {
            "id": 1,
            "method": "Page.navigate",
            "params": {"url": "https://kalavigyan.example"},
            "sessionId": "S1",
        }
    ]
    socket.say({"method": "Fetch.requestPaused", "params": {"requestId": "r1"}, "sessionId": "S1"})
    socket.say({"id": 1, "result": {"frameId": "f1"}})
    assert await call == {"frameId": "f1"}
    await settled()
    assert seen == [({"requestId": "r1"}, "S1")]
    await cdp.close()
    assert socket.closed


async def test_an_error_answer_raises_with_the_browser_s_words() -> None:
    socket = FakeSocket()
    cdp = Cdp(socket)
    call = asyncio.create_task(cdp.send("Page.navigate", {"url": "x"}))
    await settled()
    socket.say({"id": 1, "error": {"code": -32000, "message": "Cannot navigate to invalid URL"}})
    with pytest.raises(CdpError, match="Cannot navigate to invalid URL"):
        await call
    await cdp.close()


async def test_an_awaited_event_is_the_one_of_its_own_session() -> None:
    socket = FakeSocket()
    cdp = Cdp(socket)
    loaded = cdp.expect("Page.loadEventFired", "S1")
    socket.say({"method": "Page.loadEventFired", "params": {"timestamp": 1}, "sessionId": "S2"})
    await settled()
    assert not loaded.done()
    socket.say({"method": "Page.loadEventFired", "params": {"timestamp": 2}, "sessionId": "S1"})
    assert await asyncio.wait_for(loaded, 1) == {"timestamp": 2}
    await cdp.close()


async def test_a_connection_that_ends_fails_every_call_still_waiting() -> None:
    socket = FakeSocket()
    cdp = Cdp(socket)
    call = asyncio.create_task(cdp.send("Runtime.evaluate", {"expression": "1"}))
    await settled()
    socket.incoming.put_nowait(ConnectionError("gone"))
    with pytest.raises(CdpError, match="connection ended"):
        await call
    await cdp.close()
