from __future__ import annotations

import math
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime


def _seconds(value) -> float | None:
    try:
        f = float(str(value).strip())
    except TypeError, ValueError:
        return None
    return max(0.0, f) if math.isfinite(f) else None


def parse_headers(headers, now: datetime | None = None) -> float | None:
    if not headers or not hasattr(headers, "items"):
        return None
    low = {str(k).lower(): v for k, v in headers.items()}
    ms = low.get("retry-after-ms")
    if ms is not None:
        s = _seconds(ms)
        if s is not None:
            return s / 1000.0
    ra = low.get("retry-after")
    if ra is None:
        return None
    s = _seconds(ra)
    if s is not None:
        return s
    try:
        when = parsedate_to_datetime(str(ra))
    except TypeError, ValueError, IndexError:
        return None
    if when is None:
        return None
    if when.tzinfo is None:
        when = when.replace(tzinfo=UTC)
    return max(0.0, (when - (now or datetime.now(UTC))).total_seconds())


def parse_retry_info(body) -> float | None:
    if isinstance(body, list) and len(body) == 1:
        body = body[0]
    if not isinstance(body, dict):
        return None
    err = body.get("error", body)
    details = err.get("details") if isinstance(err, dict) else None
    if not isinstance(details, list):
        return None
    for d in details:
        if (
            isinstance(d, dict)
            and str(d.get("@type", "")).endswith("RetryInfo")
            and d.get("retryDelay") is not None
        ):
            raw = d["retryDelay"]
            if isinstance(raw, dict):
                s = _seconds(raw.get("seconds", 0))
                n = _seconds(raw.get("nanos", 0))
                return None if s is None else s + (n or 0.0) / 1e9
            txt = str(raw).strip()
            return _seconds(txt[:-1] if txt.endswith("s") else txt)
    return None


def retry_after_of(exc: BaseException) -> float | None:
    resp = getattr(exc, "response", None)
    headers = getattr(resp, "headers", None)
    try:
        v = parse_headers(headers)
    except Exception:
        v = None
    if v is not None:
        return v
    for attr in ("details", "body"):
        v = parse_retry_info(getattr(exc, attr, None))
        if v is not None:
            return v
    return None
