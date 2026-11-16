from __future__ import annotations

import logging
from collections.abc import Awaitable
from typing import TypeVar

from app.core.errors import ExternalFailure, Refused
from app.research.evidence_pack import REFUSED_KIND, ResearchFailure

__all__ = ["FailureLog"]

logger = logging.getLogger(__name__)

T = TypeVar("T")
MESSAGE_MAX_CHARS = 500


class FailureLog:
    def __init__(self) -> None:
        self._failures: list[ResearchFailure] = []

    @property
    def failures(self) -> tuple[ResearchFailure, ...]:
        return tuple(self._failures)

    def count(self, stage: str) -> int:
        return sum(1 for failure in self._failures if failure.stage == stage)

    async def guarded(self, call: Awaitable[T], *, stage: str, service: str, target: str) -> T | None:
        try:
            return await call
        except Refused as error:
            self._add(stage, service, target, kind=REFUSED_KIND, reason=error.reason, message=error.message)
        except ExternalFailure as error:
            self._add(stage, service, target, kind=error.kind, reason=None, message=str(error))
        except TimeoutError:
            self._add(stage, service, target, kind="unavailable", reason=None, message="took too long")
        return None

    def _add(
        self, stage: str, service: str, target: str, *, kind: str, reason: str | None, message: str
    ) -> None:
        logger.warning("%s by %s failed: %s", stage.lower(), service, kind)
        self._failures.append(
            ResearchFailure(
                stage=stage,
                service=service,
                target=target,
                kind=kind,
                reason=reason,
                message=(message or kind)[:MESSAGE_MAX_CHARS],
            )
        )
