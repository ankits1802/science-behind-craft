from __future__ import annotations

import hashlib
import json
from typing import Any

from fastapi import Request, Response, status

__all__ = [
    "PRIVATE_NO_CACHE",
    "PUBLIC_READ_CACHE",
    "PUBLIC_READ_MAX_AGE_SECONDS",
    "body_version",
    "etag_matches",
    "not_modified",
    "quoted_etag",
    "revalidation_headers",
]

PRIVATE_NO_CACHE = "private, no-cache"
PUBLIC_READ_MAX_AGE_SECONDS = 300
PUBLIC_READ_CACHE = f"public, max-age={PUBLIC_READ_MAX_AGE_SECONDS}"


def quoted_etag(version: str) -> str:
    return f'"{version}"'


def body_version(body: Any) -> str:
    text = json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def etag_matches(if_none_match: str | None, etag: str) -> bool:
    def bare(tag: str) -> str:
        tag = tag.strip()
        return tag[2:] if tag[:2].upper() == "W/" else tag

    tags = [bare(tag) for tag in (if_none_match or "").split(",") if tag.strip()]
    return "*" in tags or bare(etag) in tags


def revalidation_headers(version: str, *, cache_control: str = PRIVATE_NO_CACHE) -> dict[str, str]:
    return {"ETag": quoted_etag(version), "Cache-Control": cache_control}


def not_modified(request: Request, version: str, *, cache_control: str = PRIVATE_NO_CACHE) -> Response | None:
    headers = revalidation_headers(version, cache_control=cache_control)
    if etag_matches(request.headers.get("if-none-match"), headers["ETag"]):
        return Response(status_code=status.HTTP_304_NOT_MODIFIED, headers=headers)
    return None
