from __future__ import annotations

import re
from dataclasses import dataclass, field
from urllib.parse import urlsplit

from app.research.page_render import PICTURE_HOSTS

__all__ = ["ALLOW", "BLOCK", "PASS", "RequestGuard", "preview_refusal", "resolver_rules", "site_origin"]

PASS, ALLOW, BLOCK = "PASS", "ALLOW", "BLOCK"
DOCUMENT = "Document"
IMAGE = "Image"
SCHEMES = frozenset({"http", "https"})
PREVIEW_PATH = re.compile(r"/preview/[0-9a-f]{32}\.\d{1,12}\.[0-9a-f]{64}")
OTHER_SITE = "the renderer draws only previews on {site}"
NOT_A_PREVIEW = "the renderer draws only a page preview's private link, /preview/<token>"


def site_origin(url: str) -> str:
    parts = urlsplit(url)
    return f"{parts.scheme}://{parts.netloc}".lower()


def preview_refusal(preview_url: str, site: str) -> str | None:
    parts = urlsplit(preview_url)
    if parts.scheme not in SCHEMES or site_origin(preview_url) != site_origin(site):
        return OTHER_SITE.format(site=site_origin(site))
    if parts.query or parts.fragment or not PREVIEW_PATH.fullmatch(parts.path):
        return NOT_A_PREVIEW
    return None


def resolver_rules(site: str) -> str:
    hosts = [host for host in (urlsplit(site).hostname, *PICTURE_HOSTS) if host]
    return " , ".join(["MAP * ~NOTFOUND", *(f"EXCLUDE {host}" for host in hosts)])


@dataclass
class RequestGuard:
    site: str
    preview_url: str
    blocked: set[str] = field(default_factory=set)

    def decide(self, url: str, resource_type: str) -> str:
        parts = urlsplit(url)
        if parts.scheme not in SCHEMES or not parts.hostname:
            return self._refused(parts.scheme or url[:20])
        if site_origin(url) == site_origin(self.site):
            if resource_type == DOCUMENT and url.split("#", 1)[0] != self.preview_url:
                return self._refused(f"the site's {parts.path or '/'}")
            return PASS
        if parts.scheme == "https" and parts.hostname in PICTURE_HOSTS and resource_type == IMAGE:
            return ALLOW
        return self._refused(parts.hostname)

    def _refused(self, what: str) -> str:
        self.blocked.add(what)
        return BLOCK
