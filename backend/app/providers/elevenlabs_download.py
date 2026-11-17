from __future__ import annotations

from urllib.parse import urlsplit

import httpx

from app.core.errors import RETRYABLE_KINDS, ExternalFailure, failure_kind
from app.core.retry_after import parse_headers

from .elevenlabs_shapes import ELEVENLABS_SERVICE, off_contract

__all__ = ["DOWNLOAD_HOSTS", "DOWNLOAD_TIMEOUT", "downloaded", "http_failure"]

DOWNLOAD_HOSTS = frozenset({"storage.googleapis.com"})
DOWNLOAD_TIMEOUT = httpx.Timeout(120.0, connect=10.0)
HTTPS_PORT = 443


async def downloaded(client: httpx.AsyncClient, url: str, *, limit: int) -> bytes:
    _require_download_host(url)
    try:
        async with client.stream("GET", url, timeout=DOWNLOAD_TIMEOUT) as response:
            if not response.is_success:
                raise http_failure(response, "GET generation content")
            _require_declared_size(response, limit)
            body = bytearray()
            async for chunk in response.aiter_bytes():
                body += chunk
                if len(body) > limit:
                    raise off_contract(f"generation download (more than {limit} bytes)")
    except httpx.HTTPError as error:
        raise ExternalFailure(
            f"An ElevenLabs generation could not be fetched ({type(error).__name__})",
            kind="unavailable",
            retryable=True,
            service=ELEVENLABS_SERVICE,
        ) from None
    if not body:
        raise off_contract("generation download (0 bytes)")
    return bytes(body)


def http_failure(response: httpx.Response, call: str) -> ExternalFailure:
    kind = failure_kind(response.status_code)
    return ExternalFailure(
        f"ElevenLabs answered {response.status_code} to {call}",
        kind=kind,
        retryable=kind in RETRYABLE_KINDS,
        status=response.status_code,
        retry_after=parse_headers(response.headers),
        service=ELEVENLABS_SERVICE,
    )


def _require_download_host(url: str) -> None:
    try:
        parts = urlsplit(url)
        port = parts.port
    except ValueError:
        raise off_contract("generation link") from None
    if parts.scheme != "https" or parts.hostname not in DOWNLOAD_HOSTS:
        raise off_contract("generation link")
    if parts.username is not None or parts.password is not None or port not in (None, HTTPS_PORT):
        raise off_contract("generation link")


def _require_declared_size(response: httpx.Response, limit: int) -> None:
    declared = response.headers.get("content-length", "")
    if declared.isdigit() and int(declared) > limit:
        raise off_contract(f"generation download ({declared} bytes declared)")
