from __future__ import annotations

__all__ = [
    "FAILURE_KINDS",
    "NEXT_ROUTE_KINDS",
    "RETRYABLE_KINDS",
    "SPEND_REFUSAL_KIND",
    "STOP_KINDS",
    "AppError",
    "ExternalFailure",
    "InvalidInput",
    "NotConfigured",
    "Refused",
    "failure_kind",
    "spend_refusal",
]

FAILURE_KINDS = frozenset(
    {"rate_limit", "unavailable", "auth", "not_found", "bad_request", "refusal", "error"}
)
NEXT_ROUTE_KINDS = frozenset({"rate_limit", "unavailable", "auth", "not_found", "error"})
STOP_KINDS = frozenset({"refusal", "bad_request"})
RETRYABLE_KINDS = frozenset({"rate_limit", "unavailable"})
SPEND_REFUSAL_KIND = "ceiling"
STATUS_KINDS = {
    400: "bad_request",
    401: "auth",
    403: "auth",
    404: "not_found",
    410: "not_found",
    422: "bad_request",
}


class AppError(Exception):
    pass


class InvalidInput(AppError, ValueError):
    pass


class Refused(AppError):
    def __init__(self, reason: str, message: str) -> None:
        if not reason:
            raise ValueError("A refusal needs a reason code")
        super().__init__(message)
        self.reason = reason
        self.message = message


class NotConfigured(AppError):
    def __init__(self, name: str, message: str) -> None:
        super().__init__(message)
        self.name = name
        self.message = message


class ExternalFailure(AppError):
    def __init__(
        self,
        message: str,
        *,
        kind: str = "error",
        retryable: bool = False,
        status: int | None = None,
        retry_after: float | None = None,
        service: str | None = None,
    ) -> None:
        if kind not in FAILURE_KINDS:
            raise ValueError(f"Unknown failure kind {kind!r}; use one of {sorted(FAILURE_KINDS)}")
        super().__init__(message)
        self.kind = kind
        self.retryable = retryable
        self.status = status
        self.retry_after = retry_after
        self.service = service

    @property
    def tries_next(self) -> bool:
        return self.kind in NEXT_ROUTE_KINDS


def failure_kind(status: int) -> str:
    if status == 429:
        return "rate_limit"
    if status >= 500:
        return "unavailable"
    return STATUS_KINDS.get(status, "error")


def spend_refusal(error: BaseException) -> str | None:
    if getattr(error, "kind", None) != SPEND_REFUSAL_KIND:
        return None
    return str(error) or None
