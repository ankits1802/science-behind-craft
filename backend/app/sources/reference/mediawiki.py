from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from app.core.errors import RETRYABLE_KINDS, ExternalFailure, InvalidInput

from ..http import RatePolicy, SourceHttp
from ..records import UnusableRecord, clean_text, partial_date_of

__all__ = [
    "WIKIMEDIA_PUBLISHER",
    "WIKIMEDIA_RATE",
    "Revision",
    "action_api",
    "page_revision",
    "pages_in_order",
    "primary_language",
    "rights_text",
]

WIKIMEDIA_RATE = RatePolicy(min_interval=0.2)
WIKIMEDIA_PUBLISHER = "Wikimedia Foundation"
BASE_PARAMS = {"format": "json", "formatversion": "2", "errorformat": "plaintext"}
NOT_FOUND_CODES = frozenset({"no-such-entity", "missingtitle", "nosuchpageid", "nosuchrevid"})
RATE_LIMIT_CODES = frozenset({"ratelimited", "maxlag"})
UNAVAILABLE_CODES = frozenset({"readonly", "internal_api_error_DBQueryError"})
LANGUAGE_CODE = re.compile(r"^[a-z]{2,3}$")


@dataclass(frozen=True)
class Revision:
    id: str
    published: str | None


async def action_api(http: SourceHttp, endpoint: str, params: Mapping[str, str]) -> dict[str, Any]:
    response = await http.get(endpoint, params=BASE_PARAMS | dict(params))
    payload = response.json(http.service)
    if not isinstance(payload, dict):
        raise ExternalFailure(f"{http.service} answered with an unexpected shape", service=http.service)
    errors = payload.get("errors") or ([payload["error"]] if "error" in payload else [])
    if errors:
        raise _api_failure(http.service, errors[0])
    return payload


def pages_in_order(payload: Mapping[str, Any]) -> list[dict[str, Any]]:
    pages = list(((payload.get("query") or {}).get("pages")) or [])
    return sorted(pages, key=lambda page: page.get("index", 0))


def primary_language(language: str) -> str:
    primary = language.strip().lower().replace("_", "-").split("-")[0]
    if not LANGUAGE_CODE.match(primary):
        raise InvalidInput(f"{language!r} is not a language code")
    return primary


def rights_text(payload: Mapping[str, Any]) -> str | None:
    return clean_text((((payload.get("query") or {}).get("rightsinfo")) or {}).get("text"))


def page_revision(page: Mapping[str, Any]) -> Revision:
    revisions = page.get("revisions") or []
    if not revisions or not revisions[0].get("revid"):
        raise UnusableRecord("no revision")
    latest = revisions[0]
    return Revision(id=str(latest["revid"]), published=partial_date_of(latest.get("timestamp")))


def _api_failure(service: str, error: Mapping[str, Any]) -> ExternalFailure:
    code = str(error.get("code") or "unknown")
    kind = "error"
    if code in NOT_FOUND_CODES:
        kind = "not_found"
    elif code in RATE_LIMIT_CODES:
        kind = "rate_limit"
    elif code in UNAVAILABLE_CODES:
        kind = "unavailable"
    return ExternalFailure(
        f"{service} refused the request ({code})",
        kind=kind,
        retryable=kind in RETRYABLE_KINDS,
        service=service,
    )
