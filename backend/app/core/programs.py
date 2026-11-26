from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable, Sequence

from app.core.errors import NotConfigured

__all__ = ["FFMPEG", "Run", "run_program"]

FFMPEG = "ffmpeg"
Run = Callable[[Sequence[str], bytes], Awaitable[tuple[int, bytes]]]


async def run_program(argv: Sequence[str], content: bytes, *, seconds: float) -> tuple[int, bytes]:
    try:
        process = await asyncio.create_subprocess_exec(
            *argv,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
        )
    except FileNotFoundError as missing:
        raise NotConfigured(argv[0], f"{argv[0]} is not installed on this machine") from missing
    try:
        output, _ = await asyncio.wait_for(process.communicate(content), timeout=seconds)
    except TimeoutError:
        process.kill()
        await process.wait()
        raise
    return (-1 if process.returncode is None else process.returncode), output
