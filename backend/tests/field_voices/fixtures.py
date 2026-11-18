from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

import httpx

from app.core.config import Settings
from tests.portal_sync.fixtures import TOKEN, reference_signature, settings

RECORDED = Path(__file__).parent / "recorded"
PEER_PREFIX = "/cross-portal/peer"
AJRAKH = "Kutch-Ajrakh"
INDEX = "/field-voices"
AJRAKH_QUOTES = f"/field-voices/{AJRAKH}/quotes"
AJRAKH_PHOTOGRAPHS = f"/field-voices/{AJRAKH}/photographs"
IMAGE_HOST = "media.example.com"

Answers = dict[tuple[str, str | None], Any]


def recorded(name: str) -> dict[str, Any]:
    return json.loads((RECORDED / f"{name}.json").read_text(encoding="utf-8"))


def enabled_settings(**overrides: Any) -> Settings:
    return settings(FIELD_VOICES_ENABLED=True, FIELD_VOICES_IMAGE_HOSTS=IMAGE_HOST, **overrides)


def recorded_answers() -> Answers:
    return {
        (INDEX, None): recorded("index"),
        (AJRAKH_QUOTES, None): recorded("quotes-1"),
        (AJRAKH_QUOTES, "c2"): recorded("quotes-2"),
        (AJRAKH_PHOTOGRAPHS, None): recorded("photographs-1"),
    }


def ajrakh_entry(answers: Answers) -> dict[str, Any]:
    return next(c for c in answers[(INDEX, None)]["crafts"] if c["craftSlug"] == AJRAKH)


def portal_transport(
    answers: Answers,
    *,
    token: str = TOKEN,
    seen: list[httpx.Request] | None = None,
    signed_path: Callable[[str], str] = lambda path: path,
) -> httpx.MockTransport:
    def handler(request: httpx.Request) -> httpx.Response:
        if seen is not None:
            seen.append(request)
        path = request.url.path[request.url.path.find(PEER_PREFIX) :]
        payload = answers.get((path[len(PEER_PREFIX) :], request.url.params.get("cursor")))
        status = 200 if payload is not None else 404
        body = (
            payload if isinstance(payload, bytes) else json.dumps(payload or {"detail": "Not Found"}).encode()
        )
        nonce = request.headers.get("x-cross-portal-nonce", "")
        signature = reference_signature(token, body, method="GET", path=signed_path(path), nonce=nonce)
        return httpx.Response(status, content=body, headers={"X-Cross-Portal-Signature": signature})

    return httpx.MockTransport(handler)
