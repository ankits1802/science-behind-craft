from __future__ import annotations

from typing import Literal, Protocol, Self, runtime_checkable

from pydantic import AwareDatetime, Field, model_validator

from app.core.errors import FAILURE_KINDS, Refused

from .base import ContractModel, HttpsUrl, PartialDate

__all__ = [
    "FETCHER_FAILURE_STATUS",
    "FETCHER_HEALTH_PATH",
    "FETCHER_PATH",
    "FETCHER_REFUSED_STATUS",
    "FETCH_CONTENT_TYPES",
    "FETCH_MAX_BYTES",
    "FETCH_MAX_REDIRECTS",
    "FETCH_REFUSAL_REASONS",
    "FETCH_TEXT_MAX_CHARS",
    "FETCH_TIMEOUT_SECONDS",
    "PDF_MAX_DECOMPRESSED_BYTES",
    "PDF_MAX_PAGES",
    "FetchFailureBody",
    "FetchRefusalBody",
    "FetchRefused",
    "FetchRequest",
    "FetchedPage",
    "Fetcher",
    "PageMetadata",
]

FETCH_TIMEOUT_SECONDS = 10.0
FETCH_MAX_BYTES = 3 * 1024 * 1024
FETCH_MAX_REDIRECTS = 3
PDF_MAX_PAGES = 50
PDF_MAX_DECOMPRESSED_BYTES = 20 * 1024 * 1024
FETCH_TEXT_MAX_CHARS = 200_000
FETCH_CONTENT_TYPES = ("text/html", "application/pdf", "text/plain")
FETCH_REFUSAL_REASONS = (
    "NOT_HTTPS",
    "BAD_URL",
    "PRIVATE_ADDRESS",
    "TLS_MISMATCH",
    "TOO_MANY_REDIRECTS",
    "ROBOTS_DISALLOWED",
    "CONTENT_TYPE",
    "TOO_LARGE",
    "TIME_LIMIT",
    "PDF_LIMIT",
    "PARSE_FAILED",
)

FETCHER_PATH = "/fetch"
FETCHER_HEALTH_PATH = "/health"
FETCHER_REFUSED_STATUS = 403
FETCHER_FAILURE_STATUS = 502

ContentType = Literal[*FETCH_CONTENT_TYPES]
RefusalReason = Literal[*FETCH_REFUSAL_REASONS]
FailureKind = Literal[*sorted(FAILURE_KINDS)]


class FetchRefused(Refused):
    def __init__(self, url: str, reason: str, detail: str = "") -> None:
        if reason not in FETCH_REFUSAL_REASONS:
            raise ValueError(f"Unknown fetch refusal reason {reason!r}")
        super().__init__(reason, f"Fetch refused ({reason}){': ' + detail if detail else ''}")
        self.url = url
        self.detail = detail


class FetchRequest(ContractModel):
    url: HttpsUrl
    timeout_seconds: float = Field(default=FETCH_TIMEOUT_SECONDS, gt=0, le=FETCH_TIMEOUT_SECONDS)
    max_bytes: int = Field(default=FETCH_MAX_BYTES, gt=0, le=FETCH_MAX_BYTES)


class PageMetadata(ContractModel):
    title: str | None = None
    authors: list[str] = Field(default_factory=list)
    published: PartialDate | None = None
    licence: str | None = Field(default=None, max_length=200)
    canonical_url: HttpsUrl | None = None
    site_name: str | None = Field(default=None, max_length=300)
    language: str | None = Field(default=None, max_length=16)


class FetchedPage(ContractModel):
    url: HttpsUrl
    final_url: HttpsUrl
    redirects: list[HttpsUrl] = Field(default_factory=list, max_length=FETCH_MAX_REDIRECTS)
    status: int = Field(ge=200, le=299)
    content_type: ContentType
    bytes: int = Field(ge=0, le=FETCH_MAX_BYTES)
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    fetched_at: AwareDatetime
    text: str = Field(max_length=FETCH_TEXT_MAX_CHARS)
    truncated: bool
    metadata: PageMetadata

    @model_validator(mode="after")
    def _final_url_ends_the_chain(self) -> Self:
        expected = self.redirects[-1] if self.redirects else self.url
        if self.final_url != expected:
            raise ValueError("final_url is the last redirect, or the requested url when none")
        return self


class FetchRefusalBody(ContractModel):
    url: str = Field(max_length=4096)
    reason: RefusalReason
    detail: str = Field(default="", max_length=500)

    @classmethod
    def of(cls, refusal: FetchRefused) -> FetchRefusalBody:
        return cls(url=refusal.url, reason=refusal.reason, detail=refusal.detail[:500])

    def refusal(self) -> FetchRefused:
        return FetchRefused(self.url, self.reason, self.detail)


class FetchFailureBody(ContractModel):
    kind: FailureKind
    message: str = Field(min_length=1, max_length=500)
    retryable: bool = False
    status: int | None = None
    retry_after: float | None = Field(default=None, ge=0)


@runtime_checkable
class Fetcher(Protocol):
    async def fetch(self, request: FetchRequest) -> FetchedPage: ...
