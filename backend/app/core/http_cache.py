from __future__ import annotations

from fastapi import Request, Response, status

__all__ = [
    "PRIVATE_NO_CACHE",
    "etag_matches",
    "not_modified",
    "quoted_etag",
    "revalidated",
    "revalidation_headers",
]

PRIVATE_NO_CACHE = "private, no-cache"


def quoted_etag(version: str) -> str:
    return f'"{version}"'


def etag_matches(if_none_match: str | None, etag: str) -> bool:
    def bare(tag: str) -> str:
        tag = tag.strip()
        return tag[2:] if tag[:2].upper() == "W/" else tag

    tags = [bare(tag) for tag in (if_none_match or "").split(",") if tag.strip()]
    return "*" in tags or bare(etag) in tags


def revalidation_headers(version: str) -> dict[str, str]:
    return {"ETag": quoted_etag(version), "Cache-Control": PRIVATE_NO_CACHE}


def not_modified(request: Request, version: str) -> Response | None:
    headers = revalidation_headers(version)
    if etag_matches(request.headers.get("if-none-match"), headers["ETag"]):
        return Response(status_code=status.HTTP_304_NOT_MODIFIED, headers=headers)
    return None


def revalidated(request: Request, response: Response, version: str) -> Response | None:
    answer = not_modified(request, version)
    if answer is None:
        response.headers.update(revalidation_headers(version))
    return answer
