from __future__ import annotations

import asyncio
import os
import re
import shutil
import signal
import tempfile
from asyncio.subprocess import DEVNULL, PIPE, Process
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager, suppress

from websockets.asyncio.client import connect

from app.research.page_render import BROWSER

from .cdp import Cdp
from .failures import RenderFailed
from .guard import resolver_rules

__all__ = ["BROWSER_FLAGS", "LAUNCH_SECONDS", "browser_flags", "devtools_url", "launched"]

LAUNCH_SECONDS = 15.0
SOCKET_BYTES_MAX = 64 * 1024 * 1024
DEVTOOLS = re.compile(rb"DevTools listening on (ws://\S+)")
BROWSER_FLAGS = (
    "--headless",
    "--no-sandbox",
    "--disable-gpu",
    "--disable-dev-shm-usage",
    "--no-first-run",
    "--no-default-browser-check",
    "--disable-extensions",
    "--disable-background-networking",
    "--disable-component-update",
    "--disable-default-apps",
    "--disable-sync",
    "--metrics-recording-only",
    "--mute-audio",
    "--hide-scrollbars",
    "--force-color-profile=srgb",
    "--force-webrtc-ip-handling-policy=disable_non_proxied_udp",
    "--disable-features=Translate,MediaRouter,OptimizationHints,AutofillServerCommunication",
    "--js-flags=--max-old-space-size=512",
    "--remote-debugging-address=127.0.0.1",
    "--remote-debugging-port=0",
)
NO_BROWSER = "no browser is installed at {path}; the release installs it from infra/deploy/chromium.pin"
NO_DEVTOOLS = "the browser stopped before it opened its DevTools"
SLOW_START = "the browser did not start within {seconds} s"


def browser_flags(profile: str, site: str) -> list[str]:
    return [*BROWSER_FLAGS, f"--user-data-dir={profile}", f"--host-resolver-rules={resolver_rules(site)}"]


async def devtools_url(stream: asyncio.StreamReader) -> str:
    while line := await stream.readline():
        found = DEVTOOLS.search(line)
        if found is not None:
            return found.group(1).decode("ascii")
    raise RenderFailed(BROWSER, NO_DEVTOOLS)


@asynccontextmanager
async def launched(path: str, *, site: str) -> AsyncIterator[Cdp]:
    if not os.access(path, os.X_OK):
        raise RenderFailed(BROWSER, NO_BROWSER.format(path=path))
    profile = tempfile.mkdtemp(prefix="kv-render-")
    process = await asyncio.create_subprocess_exec(
        path,
        *browser_flags(profile, site),
        "about:blank",
        stdin=DEVNULL,
        stdout=DEVNULL,
        stderr=PIPE,
        start_new_session=True,
    )
    drain: asyncio.Task[None] | None = None
    try:
        url = await _started(process)
        drain = asyncio.create_task(_drained(process))
        socket = await connect(url, max_size=SOCKET_BYTES_MAX, ping_interval=None, compression=None)
        cdp = Cdp(socket)
        try:
            yield cdp
        finally:
            await cdp.close()
    finally:
        _stopped(process)
        await process.wait()
        if drain is not None:
            drain.cancel()
        shutil.rmtree(profile, ignore_errors=True)


async def _started(process: Process) -> str:
    if process.stderr is None:
        raise RenderFailed(BROWSER, NO_DEVTOOLS)
    try:
        return await asyncio.wait_for(devtools_url(process.stderr), LAUNCH_SECONDS)
    except TimeoutError:
        raise RenderFailed(BROWSER, SLOW_START.format(seconds=int(LAUNCH_SECONDS))) from None


async def _drained(process: Process) -> None:
    if process.stderr is not None:
        while await process.stderr.read(65536):
            pass


def _stopped(process: Process) -> None:
    if process.returncode is not None:
        return
    with suppress(ProcessLookupError):
        os.killpg(process.pid, signal.SIGKILL)
