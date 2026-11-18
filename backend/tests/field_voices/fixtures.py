from __future__ import annotations

import copy
import hashlib
import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

import httpx

from app.core.config import Settings
from tests.portal_sync.fixtures import DESIGNER_URL, FIELD_URL, TOKEN, reference_signature, settings

RECORDED = Path(__file__).parent / "recorded"
PEER_PREFIX = "/cross-portal/peer"
STATE = "/field-voices"
FR = "FIELD_REPOSITORY"
DR = "DESIGNER"
FR_HOST = "fieldrepo-media-626159998512.s3.dualstack.ap-south-1.amazonaws.com"
DR_HOST = "designrepo-media-626159998512.s3.dualstack.ap-south-1.amazonaws.com"
IMAGE_HOSTS = f"{DR_HOST},{FR_HOST}"
PREFIXES = {FR: "field", DR: "designer"}
STREAM_NAMES = ("transcripts", "images")
SCRUB_VECTORS = "field-voices-scrub-vectors"
BASES = {FR: FIELD_URL, DR: DESIGNER_URL}

Answers = dict[tuple[str, str | None, str | None], Any]


def recorded(name: str) -> dict[str, Any]:
    return json.loads((RECORDED / f"{name}.json").read_text(encoding="utf-8"))


def enabled_settings(**overrides: Any) -> Settings:
    return settings(FIELD_VOICES_ENABLED=True, FIELD_VOICES_IMAGE_HOSTS=IMAGE_HOSTS, **overrides)


def reference_revision(item: dict[str, Any]) -> str:
    signed = {key: value for key, value in item.items() if key not in ("state", "revision", "updatedAt")}
    if isinstance(signed.get("image"), dict):
        signed["image"] = {k: v for k, v in signed["image"].items() if k not in ("url", "expiresAt")}
    text = json.dumps(signed, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:32]


def reference_digest(pairs: list[tuple[str, str]]) -> str:
    lines = sorted(f"{item_id} {revision}\n" for item_id, revision in pairs)
    return hashlib.sha256("".join(lines).encode("utf-8")).hexdigest()


def resigned(change: dict[str, Any]) -> dict[str, Any]:
    change["revision"] = reference_revision(change)
    return change


def recorded_answers(portal: str) -> Answers:
    prefix = PREFIXES[portal]
    answers: Answers = {(STATE, None, None): recorded(f"{prefix}-state")}
    pages = [path for stream in STREAM_NAMES for path in RECORDED.glob(f"{prefix}-{stream}-*-*.json")]
    for path in sorted(pages):
        page = json.loads(path.read_text(encoding="utf-8"))
        answers[(f"{STATE}/{page['stream']}", page["view"], page["cursor"])] = page
    return answers


def empty_page(portal: str, stream: str, view: str, cursor: str | None) -> dict[str, Any]:
    return {
        "schemaVersion": 2,
        "portal": portal,
        "generatedAt": "2026-11-19T02:00:00Z",
        "stream": stream,
        "view": view,
        "cursor": cursor,
        "nextCursor": cursor,
        "hasMore": False,
        "changes": [],
    }


def caught_up(portal: str) -> Answers:
    answers = recorded_answers(portal)
    for (route, view, _cursor), page in list(answers.items()):
        if view is None or not page["changes"] or page["hasMore"]:
            continue
        stream = route.rsplit("/", 1)[-1]
        answers[(route, view, page["nextCursor"])] = empty_page(portal, stream, view, page["nextCursor"])
    return answers


def edited(
    answers: Answers, key: tuple[str, str | None, str | None], change: Callable[[Any], None]
) -> Answers:
    copied = copy.deepcopy(answers)
    change(copied[key])
    return copied


def portal_transport(
    answers: Answers,
    *,
    token: str = TOKEN,
    seen: list[httpx.Request] | None = None,
    status: int | None = None,
) -> httpx.MockTransport:
    def handler(request: httpx.Request) -> httpx.Response:
        if seen is not None:
            seen.append(request)
        path = request.url.path[request.url.path.find(PEER_PREFIX) :]
        key = (path[len(PEER_PREFIX) :], request.url.params.get("view"), request.url.params.get("cursor"))
        payload = answers.get(key)
        code = status or (200 if payload is not None else 404)
        body = json.dumps(payload if payload is not None else {"detail": "Not Found"}).encode()
        nonce = request.headers.get("x-cross-portal-nonce", "")
        signature = reference_signature(token, body, method="GET", path=path, nonce=nonce)
        return httpx.Response(code, content=body, headers={"X-Cross-Portal-Signature": signature})

    return httpx.MockTransport(handler)
