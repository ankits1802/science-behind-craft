from __future__ import annotations

import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from types import TracebackType
from urllib.parse import urlsplit

import httpx

__all__ = [
    "BROWSER_HEADERS",
    "HOST_DELAY_SECONDS",
    "MAX_RESPONSE_BYTES",
    "FetchFailed",
    "Fetched",
    "PoliteHttp",
]

BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/142.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/pdf;q=0.9,text/plain;q=0.8,*/*;q=0.5",
    "Accept-Language": "en-IN,en;q=0.9",
}
HOST_DELAY_SECONDS = 1.5
MAX_RESPONSE_BYTES = 40 * 1024 * 1024
CONNECT_TIMEOUT_SECONDS = 15.0
READ_TIMEOUT_SECONDS = 60.0
MAX_REDIRECTS = 10
FAILURE_STATUS = 400


class FetchFailed(Exception):
    def __init__(self, url: str, reason: str) -> None:
        super().__init__(f"{url}: {reason}")
        self.url = url
        self.reason = reason


@dataclass(frozen=True)
class Fetched:
    url: str
    final_url: str
    status: int
    media_type: str
    charset: str | None
    body: bytes
    fetched_at: datetime


class PoliteHttp:
    def __init__(
        self,
        *,
        client: httpx.Client | None = None,
        delay_seconds: float = HOST_DELAY_SECONDS,
        max_bytes: int = MAX_RESPONSE_BYTES,
        clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self._client = client or httpx.Client(
            headers=BROWSER_HEADERS,
            follow_redirects=True,
            max_redirects=MAX_REDIRECTS,
            timeout=httpx.Timeout(READ_TIMEOUT_SECONDS, connect=CONNECT_TIMEOUT_SECONDS),
        )
        self._delay = delay_seconds
        self._max_bytes = max_bytes
        self._clock = clock
        self._sleep = sleep
        self._guard = threading.Lock()
        self._hosts: dict[str, threading.Lock] = {}
        self._last: dict[str, float] = {}

    def __enter__(self) -> PoliteHttp:
        return self

    def __exit__(
        self, kind: type[BaseException] | None, error: BaseException | None, trace: TracebackType | None
    ) -> None:
        self.close()

    def close(self) -> None:
        self._client.close()

    def get(self, url: str) -> Fetched:
        host = (urlsplit(url).hostname or "").casefold()
        with self._host_lock(host):
            self._wait_for(host)
            try:
                return self._fetched(url)
            finally:
                self._last[host] = self._clock()

    def _host_lock(self, host: str) -> threading.Lock:
        with self._guard:
            return self._hosts.setdefault(host, threading.Lock())

    def _wait_for(self, host: str) -> None:
        last = self._last.get(host)
        if last is not None:
            remaining = self._delay - (self._clock() - last)
            if remaining > 0:
                self._sleep(remaining)

    def _fetched(self, url: str) -> Fetched:
        try:
            with self._client.stream("GET", url) as response:
                if response.status_code >= FAILURE_STATUS:
                    raise FetchFailed(url, f"HTTP {response.status_code}")
                body = self._body(url, response)
                content_type = response.headers.get("content-type", "")
                return Fetched(
                    url=url,
                    final_url=str(response.url),
                    status=response.status_code,
                    media_type=content_type.split(";", 1)[0].strip().casefold(),
                    charset=response.charset_encoding,
                    body=body,
                    fetched_at=datetime.now(UTC),
                )
        except httpx.HTTPError as error:
            raise FetchFailed(url, f"{type(error).__name__}: {error}") from None

    def _body(self, url: str, response: httpx.Response) -> bytes:
        declared = response.headers.get("content-length", "")
        if declared.isdigit() and int(declared) > self._max_bytes:
            raise FetchFailed(url, f"the response declares {declared} bytes, over the {self._max_bytes} cap")
        chunks: list[bytes] = []
        received = 0
        for chunk in response.iter_bytes():
            received += len(chunk)
            if received > self._max_bytes:
                raise FetchFailed(url, f"the response passed the {self._max_bytes} byte cap")
            chunks.append(chunk)
        return b"".join(chunks)
