from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Usage:
    input_tokens: int | None = None
    output_tokens: int | None = None
    cached_input_tokens: int | None = None
    cache_write_tokens: int | None = None


def _get(obj, name: str):
    if obj is None:
        return None
    if isinstance(obj, dict):
        return obj.get(name)
    return getattr(obj, name, None)


def _int(v) -> int | None:
    if v is None or isinstance(v, bool):
        return None
    try:
        return int(v)
    except TypeError, ValueError:
        return None


def anthropic_usage(u) -> Usage:
    uncached = _int(_get(u, "input_tokens"))
    read = _int(_get(u, "cache_read_input_tokens"))
    write = _int(_get(u, "cache_creation_input_tokens"))
    total = None if uncached is None else uncached + (read or 0) + (write or 0)
    return Usage(total, _int(_get(u, "output_tokens")), read, write)


def openai_usage(u) -> Usage:
    details = _get(u, "prompt_tokens_details")
    return Usage(
        _int(_get(u, "prompt_tokens")),
        _int(_get(u, "completion_tokens")),
        _int(_get(details, "cached_tokens")),
        _int(_get(details, "cache_write_tokens")),
    )


def gemini_cached_tokens(u) -> int | None:
    return _int(_get(u, "cached_content_token_count"))
