from __future__ import annotations

import json
import re
from urllib.parse import urlencode

__all__ = [
    "CDX_URL",
    "SNAPSHOT",
    "latest_snapshot",
    "latest_snapshot_query",
    "raw_snapshot_url",
    "snapshot_of",
]

CDX_URL = "https://web.archive.org/cdx/search/cdx"
SNAPSHOT = re.compile(
    r"^https?://web\.archive\.org/web/(?P<timestamp>\d{4,14})(?:[a-z]{2}_)?/(?P<original>https?://.+)$"
)


def latest_snapshot_query(url: str) -> str:
    query = {
        "url": url,
        "output": "json",
        "fl": "timestamp,original",
        "filter": "statuscode:200",
        "limit": "-1",
    }
    return f"{CDX_URL}?{urlencode(query)}"


def latest_snapshot(cdx_body: str) -> str | None:
    text = cdx_body.strip()
    rows = json.loads(text) if text else []
    if not isinstance(rows, list) or len(rows) < 2:
        return None
    header, *captures = rows
    timestamp, original = (captures[-1][header.index(field)] for field in ("timestamp", "original"))
    return snapshot_of(str(timestamp), str(original))


def snapshot_of(timestamp: str, original: str) -> str:
    return f"https://web.archive.org/web/{timestamp}id_/{original}"


def raw_snapshot_url(url: str) -> str:
    found = SNAPSHOT.match(url)
    return url if found is None else snapshot_of(found["timestamp"], found["original"])
