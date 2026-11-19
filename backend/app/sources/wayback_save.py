from __future__ import annotations

from urllib.parse import urljoin

import httpx

from app.core.errors import RETRYABLE_KINDS, ExternalFailure, failure_kind

__all__ = ["WAYBACK_ORIGIN", "WAYBACK_SAVE_SERVICE", "WAYBACK_SAVE_TIMEOUT_SECONDS", "WaybackSaver"]

WAYBACK_ORIGIN = "https://web.archive.org"
WAYBACK_SAVE_PATH = "/save/"
WAYBACK_SAVE_SERVICE = "wayback-save"
WAYBACK_SAVE_TIMEOUT_SECONDS = 120.0
REDIRECTS = frozenset({301, 302, 303, 307, 308})


class WaybackSaver:
    def __init__(self, client: httpx.AsyncClient) -> None:
        self.client = client

    async def save(self, url: str) -> str:
        try:
            response = await self.client.get(
                f"{WAYBACK_ORIGIN}{WAYBACK_SAVE_PATH}{url}", timeout=WAYBACK_SAVE_TIMEOUT_SECONDS
            )
        except httpx.TimeoutException:
            raise _failure("did not answer in time", kind="unavailable") from None
        except httpx.HTTPError:
            raise _failure("could not be reached", kind="unavailable") from None
        return _snapshot(response)


def _snapshot(response: httpx.Response) -> str:
    status = response.status_code
    if status in REDIRECTS:
        location = response.headers.get("location")
    elif 200 <= status < 300:
        location = response.headers.get("content-location")
    else:
        raise _failure(f"answered {status}", kind=failure_kind(status), status=status)
    if not location:
        raise _failure(f"answered {status} without naming the snapshot")
    return urljoin(WAYBACK_ORIGIN, location)


def _failure(what: str, *, kind: str = "error", status: int | None = None) -> ExternalFailure:
    return ExternalFailure(
        f"the Wayback Machine's save endpoint {what}",
        kind=kind,
        retryable=kind in RETRYABLE_KINDS,
        status=status,
        service=WAYBACK_SAVE_SERVICE,
    )
