from __future__ import annotations

import base64
import binascii
import hashlib
import hmac
import json
from collections.abc import Mapping
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.core.config import get_settings
from app.core.security import secret_key

from .mcp_protocol import INVALID_PARAMS, RequestError

__all__ = [
    "ASKED",
    "ASKED_AFTER",
    "UPLOADED",
    "SealedCall",
    "arguments_digest",
    "opened_state",
    "sealed_state",
]

ASKED, ASKED_AFTER, UPLOADED = "asked", "asked_after", "uploaded"
STATE_CONTEXT = b"kalavigyan/mcp-request-state/1"
SEPARATOR = "."
REFUSED = "requestState is not one this server issued for this call; call the tool again without it"
EXPIRED = "requestState has expired; call the tool again without it"


class SealedCall(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    tool: str
    arguments: str
    principal: str | None
    purpose: Literal["asked", "asked_after", "uploaded"]
    keys: tuple[str, ...] = ()
    refs: Mapping[str, str] = Field(default_factory=dict)
    expires: int

    def matches(self, tool: str, arguments: Any, principal: str | None) -> bool:
        return (self.tool, self.arguments, self.principal) == (tool, arguments_digest(arguments), principal)


def arguments_digest(arguments: Any) -> str:
    text = json.dumps(_canonical(arguments), ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sealed_state(call: SealedCall) -> str:
    body = _encoded(call.model_dump_json().encode("utf-8"))
    return f"{body}{SEPARATOR}{_encoded(_mac(body))}"


def opened_state(state: Any, now: datetime) -> SealedCall:
    body, _, mac = state.partition(SEPARATOR) if isinstance(state, str) else ("", "", "")
    try:
        expected = _mac(body)
        if not body or not hmac.compare_digest(_decoded(mac), expected):
            raise RequestError(INVALID_PARAMS, REFUSED)
        call = SealedCall.model_validate_json(_decoded(body))
    except ValueError, binascii.Error, ValidationError:
        raise RequestError(INVALID_PARAMS, REFUSED) from None
    if call.expires <= int(now.timestamp()):
        raise RequestError(INVALID_PARAMS, EXPIRED)
    return call


def _canonical(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _canonical(item) for key, item in value.items()}
    if isinstance(value, list | tuple):
        return [_canonical(item) for item in value]
    if isinstance(value, float) and value.is_integer():
        return int(value)
    return value


def _mac(body: str) -> bytes:
    key = hmac.new(
        secret_key("JWT_SECRET", get_settings().jwt_secret), STATE_CONTEXT, hashlib.sha256
    ).digest()
    return hmac.new(key, body.encode("ascii"), hashlib.sha256).digest()


def _encoded(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def _decoded(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))
