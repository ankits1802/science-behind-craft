from __future__ import annotations

import base64
import binascii
from collections.abc import Mapping
from typing import Any

from .mcp_meta import PROTOCOL_KEY, is_modern, request_meta
from .mcp_protocol import (
    HEADER_MISMATCH,
    INVALID_PARAMS,
    METHOD_NOT_FOUND,
    MISSING_CAPABILITY,
    MODERN_VERSION,
    UNSUPPORTED_VERSION,
    RequestError,
)

__all__ = [
    "METHOD_HEADER",
    "NAME_HEADER",
    "VERSION_HEADER",
    "header_mismatch",
    "header_value",
    "modern_status",
    "refused_up_front",
]

VERSION_HEADER = "mcp-protocol-version"
METHOD_HEADER = "mcp-method"
NAME_HEADER = "mcp-name"
SENTINEL_START, SENTINEL_END = "=?base64?", "?="
NAMED: Mapping[str, str] = {
    "tools/call": "name",
    "prompts/get": "name",
    "resources/read": "uri",
    "tasks/get": "taskId",
    "tasks/update": "taskId",
    "tasks/cancel": "taskId",
}
BAD_REQUEST, NOT_FOUND, OK = 400, 404, 200
REFUSED_CODES = frozenset({HEADER_MISMATCH, MISSING_CAPABILITY, UNSUPPORTED_VERSION, INVALID_PARAMS})
MISSING = "Header mismatch: the {header} header is missing"
NO_META = f"a request of protocol {MODERN_VERSION} carries {PROTOCOL_KEY} in its _meta"
DIFFERS = "Header mismatch: the {header} header does not match the body's {field}"


def header_value(value: str) -> str | None:
    if not (value.startswith(SENTINEL_START) and value.endswith(SENTINEL_END)):
        return value if value.isascii() and value == value.strip() else None
    encoded = value[len(SENTINEL_START) : -len(SENTINEL_END)]
    try:
        return base64.b64decode(encoded, validate=True).decode("utf-8")
    except binascii.Error, UnicodeDecodeError:
        return None


def refused_up_front(headers: Mapping[str, str], message: Any) -> RequestError | None:
    if not is_modern(message):
        unmarked = isinstance(message, Mapping) and "id" in message and message.get("method") != "initialize"
        modern_header = headers.get(VERSION_HEADER) == MODERN_VERSION
        return RequestError(INVALID_PARAMS, NO_META) if unmarked and modern_header else None
    mismatch = header_mismatch(headers, message)
    if mismatch is not None:
        return mismatch
    try:
        request_meta(message["method"], message["params"])
    except RequestError as refused:
        return refused
    return None


def header_mismatch(headers: Mapping[str, str], message: Any) -> RequestError | None:
    if not is_modern(message):
        return None
    params = message.get("params") or {}
    expected = {
        VERSION_HEADER: (params["_meta"][PROTOCOL_KEY], f"_meta {PROTOCOL_KEY}"),
        METHOD_HEADER: (message["method"], "method"),
    }
    named = NAMED.get(message["method"])
    if named is not None:
        expected[NAME_HEADER] = (params.get(named), f"params.{named}")
    for header, (value, field) in expected.items():
        given = headers.get(header)
        if given is None:
            return RequestError(HEADER_MISMATCH, MISSING.format(header=header))
        shown = header_value(given) if header == NAME_HEADER else given
        if shown is None or shown != value:
            return RequestError(HEADER_MISMATCH, DIFFERS.format(header=header, field=field))
    return None


def modern_status(reply: Mapping[str, Any] | None) -> int:
    error = reply.get("error") if reply is not None else None
    code = error.get("code") if isinstance(error, Mapping) else None
    if code == METHOD_NOT_FOUND:
        return NOT_FOUND
    return BAD_REQUEST if code in REFUSED_CODES else OK
