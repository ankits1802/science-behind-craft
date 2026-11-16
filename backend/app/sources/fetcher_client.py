from __future__ import annotations

import httpx
from pydantic import ValidationError

from app.core.errors import ExternalFailure
from app.research.fetcher import (
    FETCHER_FAILURE_STATUS,
    FETCHER_PATH,
    FETCHER_REFUSED_STATUS,
    FetchedPage,
    FetchFailureBody,
    FetchRefusalBody,
    FetchRequest,
)

__all__ = ["FETCHER_MARGIN_SECONDS", "FETCHER_SERVICE", "FetcherClient"]

FETCHER_MARGIN_SECONDS = 5.0
FETCHER_SERVICE = "fetcher"


class FetcherClient:
    def __init__(self, base_url: str, client: httpx.AsyncClient) -> None:
        self.endpoint = base_url.rstrip("/") + FETCHER_PATH
        self.client = client

    async def fetch(self, request: FetchRequest) -> FetchedPage:
        try:
            response = await self.client.post(
                self.endpoint,
                json=request.model_dump(mode="json"),
                timeout=request.timeout_seconds + FETCHER_MARGIN_SECONDS,
            )
        except httpx.TimeoutException:
            raise _failure("the fetcher did not answer in time", kind="unavailable") from None
        except httpx.HTTPError:
            raise _failure("the fetcher could not be reached", kind="unavailable") from None
        return _page_from(response)


def _page_from(response: httpx.Response) -> FetchedPage:
    try:
        if response.status_code == 200:
            return FetchedPage.model_validate_json(response.content)
        if response.status_code == FETCHER_REFUSED_STATUS:
            raise FetchRefusalBody.model_validate_json(response.content).refusal()
        if response.status_code == FETCHER_FAILURE_STATUS:
            body = FetchFailureBody.model_validate_json(response.content)
            raise ExternalFailure(
                body.message,
                kind=body.kind,
                retryable=body.retryable,
                status=body.status,
                retry_after=body.retry_after,
                service=FETCHER_SERVICE,
            )
    except ValidationError:
        raise _failure(f"the fetcher answered {response.status_code} with a body off the contract") from None
    raise _failure(
        f"the fetcher answered {response.status_code}",
        kind="unavailable" if response.status_code >= 500 else "error",
    )


def _failure(message: str, *, kind: str = "error") -> ExternalFailure:
    return ExternalFailure(message, kind=kind, retryable=kind == "unavailable", service=FETCHER_SERVICE)
