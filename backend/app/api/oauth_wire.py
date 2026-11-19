from __future__ import annotations

import json
from typing import Any
from urllib.parse import parse_qsl

from fastapi import Request
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from app.research.oauth_contract import ClientRegistration
from app.research.oauth_rules import INVALID_CLIENT_METADATA, INVALID_REQUEST, OAuthError

__all__ = ["FORM_TYPE", "NO_STORE", "form_fields", "oauth_error_response", "registration_from"]

FORM_TYPE = "application/x-www-form-urlencoded"
BODY_MAX_BYTES = 16 * 1024
NO_STORE = {"Cache-Control": "no-store", "Pragma": "no-cache"}


async def form_fields(request: Request) -> dict[str, str]:
    if _media_type(request) != FORM_TYPE:
        raise OAuthError(INVALID_REQUEST, f"send the parameters as {FORM_TYPE}")
    body = await _body(request)
    try:
        pairs = parse_qsl(body.decode("utf-8"), keep_blank_values=True)
    except UnicodeDecodeError as unreadable:
        raise OAuthError(INVALID_REQUEST, "the body is not UTF-8") from unreadable
    fields: dict[str, str] = {}
    for key, value in pairs:
        if key in fields:
            raise OAuthError(INVALID_REQUEST, f"{key} is sent more than once")
        if value:
            fields[key] = value
    return fields


async def registration_from(request: Request) -> ClientRegistration:
    try:
        body: Any = json.loads(await _body(request))
    except ValueError as unreadable:
        raise OAuthError(INVALID_CLIENT_METADATA, "the body is not JSON") from unreadable
    try:
        return ClientRegistration.model_validate(body)
    except ValidationError as refused:
        raise OAuthError(
            INVALID_CLIENT_METADATA, f"these fields do not fit: {_wrong_fields(refused)}"
        ) from refused


def oauth_error_response(refused: OAuthError) -> JSONResponse:
    return JSONResponse(
        {"error": refused.error, "error_description": refused.description},
        status_code=refused.status,
        headers=NO_STORE,
    )


def _media_type(request: Request) -> str:
    return request.headers.get("content-type", "").split(";")[0].strip().lower()


async def _body(request: Request) -> bytes:
    body = await request.body()
    if len(body) > BODY_MAX_BYTES:
        raise OAuthError(INVALID_REQUEST, f"the body is at most {BODY_MAX_BYTES} bytes")
    return body


def _wrong_fields(refused: ValidationError) -> str:
    return ", ".join(
        sorted({str(problem["loc"][0]) if problem["loc"] else "body" for problem in refused.errors()})
    )
