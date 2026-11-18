from __future__ import annotations

import asyncio
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field

__all__ = ["KeptValue"]


@dataclass
class KeptValue[T]:
    lifetime_seconds: float
    clock: Callable[[], float] = time.monotonic
    _kept: tuple[float, T] | None = None
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock)

    def __post_init__(self) -> None:
        if self.lifetime_seconds <= 0:
            raise ValueError(f"a kept value lives a positive number of seconds, not {self.lifetime_seconds}")

    async def value(self, build: Callable[[], Awaitable[T]]) -> T:
        async with self._lock:
            now = self.clock()
            if self._kept is not None and now - self._kept[0] < self.lifetime_seconds:
                return self._kept[1]
            built = await build()
            self._kept = (now, built)
            return built
