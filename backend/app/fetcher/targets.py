from __future__ import annotations

import ipaddress
from dataclasses import dataclass
from urllib.parse import urljoin, urlsplit, urlunsplit

from app.research.base import URL_MAX_CHARS
from app.research.fetcher import FetchRefused

__all__ = ["HTTPS_PORT", "Target", "checked_target", "redirect_target"]

HTTPS_PORT = 443


@dataclass(frozen=True)
class Target:
    url: str
    host: str
    netloc: str
    path: str
    port: int = HTTPS_PORT


def checked_target(url: str) -> Target:
    if len(url) > URL_MAX_CHARS or any(ch.isspace() for ch in url):
        raise FetchRefused(url, "BAD_URL", f"a URL is at most {URL_MAX_CHARS} characters with no spaces")
    try:
        parts = urlsplit(url)
        port = parts.port
    except ValueError:
        raise FetchRefused(url, "BAD_URL", "the URL does not parse") from None
    if parts.scheme.lower() != "https":
        raise FetchRefused(url, "NOT_HTTPS", f"scheme {parts.scheme or 'none'!r}")
    if parts.username is not None or parts.password is not None:
        raise FetchRefused(url, "BAD_URL", "credentials in the URL")
    if port not in (None, HTTPS_PORT):
        raise FetchRefused(url, "BAD_URL", f"port {port}; only {HTTPS_PORT} is fetched")
    host, netloc = _host(url, parts.hostname)
    path = urlunsplit(("", "", parts.path or "/", parts.query, ""))
    url = urlunsplit(("https", netloc, parts.path or "/", parts.query, ""))
    return Target(url=url, host=host, netloc=netloc, path=path)


def redirect_target(current: Target, location: str) -> Target:
    return checked_target(urljoin(current.url, location.strip()))


def _host(url: str, hostname: str | None) -> tuple[str, str]:
    if not hostname:
        raise FetchRefused(url, "BAD_URL", "no host")
    try:
        literal = ipaddress.ip_address(hostname)
    except ValueError:
        literal = None
    if literal is not None:
        text = str(literal)
        return text, f"[{text}]" if literal.version == 6 else text
    try:
        name = hostname.encode("idna").decode("ascii").lower()
    except UnicodeError:
        raise FetchRefused(url, "BAD_URL", "the host is not a valid name") from None
    return name, name
