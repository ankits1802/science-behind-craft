from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass, field

from app.core.errors import InvalidInput

__all__ = ["Deadline"]


@dataclass(frozen=True)
class Deadline:
    at: float
    clock: Callable[[], float] = field(default=time.monotonic, compare=False)

    @classmethod
    def after(cls, seconds: float, *, clock: Callable[[], float] = time.monotonic) -> Deadline:
        if seconds <= 0:
            raise InvalidInput(f"A time budget must be positive, not {seconds} seconds")
        return cls(at=clock() + seconds, clock=clock)

    def passed(self) -> bool:
        return self.clock() >= self.at
