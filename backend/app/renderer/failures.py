from __future__ import annotations

__all__ = ["RenderFailed"]


class RenderFailed(Exception):
    def __init__(self, reason: str, message: str) -> None:
        super().__init__(message)
        self.reason = reason
        self.message = message
