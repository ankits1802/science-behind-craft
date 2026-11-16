from __future__ import annotations

import base64
import hashlib
import hmac
import json
from collections.abc import Mapping
from datetime import datetime, timedelta
from typing import Any

from app.core.errors import Refused
from app.core.security import secret_key

from .records import JobRecord

__all__ = [
    "BUNDLE_KEY_NAME",
    "BUNDLE_LIFETIME",
    "BUNDLE_TOOL",
    "bundle_key",
    "opened_bundle",
    "sealed_bundle",
]

BUNDLE_TOOL = "media.generate/v1"
BUNDLE_LIFETIME = timedelta(hours=24)
BUNDLE_KEY_NAME = "MEDIA_BUNDLE_HMAC_KEY"
MAC_FIELD = "mac"


def bundle_key(value: str | None) -> bytes:
    return secret_key(BUNDLE_KEY_NAME, value)


def sealed_bundle(key: bytes, job: JobRecord, *, role: str, now: datetime) -> dict[str, Any]:
    payload = {
        "tool": BUNDLE_TOOL,
        "args": _args(job),
        "requester": {"userId": str(job.requested_by), "role": role},
        "target": {"jobId": str(job.id), "stageId": str(job.stage_id)},
        "expiresAt": (now + BUNDLE_LIFETIME).isoformat(),
    }
    return {**payload, MAC_FIELD: _mac(key, payload)}


def opened_bundle(key: bytes, bundle: Mapping[str, Any] | None, job: JobRecord, *, now: datetime) -> str:
    if not isinstance(bundle, Mapping):
        raise Refused("bundle_missing", f"Media job {job.id} has no bundle")
    payload = {name: value for name, value in bundle.items() if name != MAC_FIELD}
    given = bundle.get(MAC_FIELD)
    if not isinstance(given, str) or not hmac.compare_digest(given, _mac(key, payload)):
        raise Refused("bundle_forged", f"Media job {job.id} carries a bundle that fails its HMAC")
    if payload.get("tool") != BUNDLE_TOOL or payload.get("args") != _args(job):
        raise Refused("bundle_mismatch", f"Media job {job.id} no longer matches its bundle")
    target = payload.get("target") or {}
    requester = payload.get("requester") or {}
    if target != {"jobId": str(job.id), "stageId": str(job.stage_id)}:
        raise Refused("bundle_mismatch", f"Media job {job.id} bundle names another target")
    if requester.get("userId") != str(job.requested_by) or not isinstance(requester.get("role"), str):
        raise Refused("bundle_mismatch", f"Media job {job.id} bundle names another requester")
    if _expiry(payload.get("expiresAt"), job) <= now:
        raise Refused("bundle_expired", f"Media job {job.id} bundle has expired")
    return requester["role"]


def _args(job: JobRecord) -> dict[str, Any]:
    return {
        "kind": job.kind,
        "stageId": str(job.stage_id),
        "claimIds": [str(claim_id) for claim_id in job.claim_ids],
        "promptHash": job.prompt_hash,
        "promptSha256": hashlib.sha256(job.prompt.encode("utf-8")).hexdigest(),
        "model": job.model,
        "styleHint": job.style_hint,
    }


def _mac(key: bytes, payload: Mapping[str, Any]) -> str:
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    digest = hmac.new(key, canonical.encode("utf-8"), hashlib.sha256).digest()
    return base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")


def _expiry(value: Any, job: JobRecord) -> datetime:
    try:
        expiry = datetime.fromisoformat(str(value))
    except ValueError:
        raise Refused("bundle_mismatch", f"Media job {job.id} bundle has no readable expiry") from None
    if expiry.tzinfo is None:
        raise Refused("bundle_mismatch", f"Media job {job.id} bundle expiry has no time zone")
    return expiry
