from __future__ import annotations

import re
from collections.abc import Awaitable, Callable, Sequence

from app.core.errors import InvalidInput
from app.core.programs import FFMPEG, Run, run_program

__all__ = [
    "DECODE_ARGS",
    "DECODE_TIMEOUT_SECONDS",
    "FFMPEG",
    "Measure",
    "Run",
    "decoded_seconds",
    "run_decoder",
]

DECODE_TIMEOUT_SECONDS = 20.0
DECODE_ARGS = (
    "-hide_banner",
    "-nostats",
    "-v",
    "error",
    "-i",
    "pipe:0",
    "-map",
    "0:a:0",
    "-f",
    "null",
    "-progress",
    "pipe:1",
    "-",
)
OUT_TIME = re.compile(rb"^out_time_us=(\d+)\s*$", re.MULTILINE)
MICROSECONDS = 1_000_000

Measure = Callable[[bytes], Awaitable[float]]


async def decoded_seconds(content: bytes, *, run: Run | None = None) -> float:
    code, progress = await (run or run_decoder)((FFMPEG, *DECODE_ARGS), content)
    times = OUT_TIME.findall(progress)
    if code != 0 or not times:
        raise InvalidInput("The recording is not audio that can be decoded")
    seconds = int(times[-1]) / MICROSECONDS
    if seconds <= 0:
        raise InvalidInput("The recording holds no sound")
    return seconds


async def run_decoder(argv: Sequence[str], content: bytes) -> tuple[int, bytes]:
    try:
        return await run_program(argv, content, seconds=DECODE_TIMEOUT_SECONDS)
    except TimeoutError:
        raise InvalidInput("The recording took too long to decode") from None
