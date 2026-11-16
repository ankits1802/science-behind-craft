from __future__ import annotations

import copy
import hashlib
import hmac
import json
from collections.abc import Callable
from typing import Any

import httpx

from app.core.config import Settings
from app.services.portal_craft_plan import KnownCategory, KnownCraft, KnownState, KnownSubCategory

TOKEN = "kalavigyan-test-token-" + "x" * 20
DESIGNER_URL = "https://designer.example.com/api"
FIELD_URL = "https://field.example.com/api"
FEED_PATH = "/cross-portal/peer/crafts"
SYNCED_AT = "2026-11-16T03:00:00+00:00"

TEXTILES = "Textiles-based-Craft"
BLOCK_PRINTING = "Hand-Block-Printing"


def settings(**overrides: Any) -> Settings:
    values: dict[str, Any] = {
        "DATABASE_URL": "postgresql://kalavigyan:kalavigyan@localhost:5432/kalavigyan_test",
        "JWT_SECRET": "test-only-signing-key-" + "k" * 40,
        "MASTER_ADMIN_EMAIL": "owner@example.com",
        "CROSS_PORTAL_TOKEN": TOKEN,
        "DESIGNER_PORTAL_API_URL": DESIGNER_URL,
        "FIELD_REPOSITORY_API_URL": FIELD_URL,
    }
    values.update(overrides)
    return Settings(_env_file=None, **values)


def reference_signature(token: str, body: bytes, *, method: str, path: str, nonce: str) -> str:
    material = f"{method}\n{path}\n{nonce}\n".encode() + body
    return hmac.new(token.encode(), material, hashlib.sha256).hexdigest()


def craft(
    craft_id: str,
    slug: str,
    name: str,
    *,
    sub: str | None = "sub-hbp",
    status: str = "ACTIVE",
    merged_into: str | None = None,
    **extra: Any,
) -> dict[str, Any]:
    return {
        "id": craft_id,
        "slug": slug,
        "name": name,
        "subCategoryId": sub,
        "status": status,
        "mergedIntoId": merged_into,
        "stateOfOrigin": [],
        "stateOfPractice": ["Rajasthan"],
        "isCatchAll": False,
        "aliases": [],
        "updatedAt": "2026-11-10T08:00:00Z",
        **extra,
    }


def designer_payload() -> dict[str, Any]:
    return {
        "schemaVersion": 1,
        "portal": "DESIGNER",
        "generatedAt": "2026-11-16T02:59:00Z",
        "categories": [
            {
                "id": "cat-tex",
                "slug": TEXTILES,
                "name": "Textiles based Craft Category",
                "sortOrder": 1,
                "subCategories": [{"id": "sub-hbp", "slug": BLOCK_PRINTING, "name": "Hand Block Printing"}],
            },
            {
                "id": "cat-paper",
                "slug": "Paper-Crafts",
                "name": "Paper Crafts",
                "sortOrder": 9,
                "subCategories": [{"id": "sub-paper", "slug": "Paper-Cutting", "name": "Paper Cutting"}],
            },
        ],
        "crafts": [
            craft("d1", "Kutch-Ajrakh", "Ajrakh", aliases=["Ajrak", "अजरख"]),
            craft("d2", "Dabu-Print", "Dabu Print", craftCode="dabu", localName="दाबू"),
            craft("d3", "Dabu-Printing", "Dabu Printing", status="MERGED", merged_into="d2"),
            craft("d4", "Sanjhi", "Sanjhi", sub="sub-paper"),
        ],
        "codes": [{"code": "dabu", "name": "Dabu"}],
        "spellings": [{"spelling": "daboo", "label": "Daboo", "craftCode": "dabu", "source": "SHARED"}],
        "unknownFutureField": {"ignored": True},
    }


def field_payload() -> dict[str, Any]:
    payload = designer_payload()
    payload["portal"] = "FIELD_REPOSITORY"
    payload["categories"][0]["subCategories"][0]["id"] = "fr-sub-hbp"
    payload["categories"][1]["subCategories"][0]["id"] = "fr-sub-paper"
    payload["crafts"] = [
        craft("f1", "dabu-print", "Dabu  print", sub="fr-sub-hbp"),
        craft("f2", "Sanjhi", "Sanjhi", sub="fr-sub-paper", status="LEGACY"),
        craft("f3", "Bagru-Print", "Bagru Print", sub="fr-sub-hbp", status="MERGED", merged_into="f1"),
        craft("f4", "Pattachitra-Odisha", "Pattachitra", sub=None),
    ]
    payload["codes"] = [{"code": "dabu", "name": "Dabu"}, {"code": "patta", "name": "Pattachitra"}]
    payload["spellings"] = [{"spelling": "daboo", "label": "Daboo", "craftCode": "dabu", "source": "SHARED"}]
    return payload


def known_state(*crafts: KnownCraft) -> KnownState:
    master = (
        KnownCraft(
            "Kutch-Ajrakh", "Ajrakh Print of Kutch", BLOCK_PRINTING, "ACTIVE", None, {"masterId": "cmc1"}
        ),
        KnownCraft("Bagru-Print", "Bagru Print", BLOCK_PRINTING, "ACTIVE", None, {"masterId": "cmc2"}),
    )
    return KnownState(
        categories=(KnownCategory(TEXTILES, "Textiles based Craft Category"),),
        sub_categories=(KnownSubCategory(BLOCK_PRINTING, "Hand Block Printing", TEXTILES),),
        crafts=(*master, *crafts),
        codes=frozenset({"ajrakh"}),
        spellings=frozenset(),
        master_slugs=frozenset({"Kutch-Ajrakh", "Bagru-Print"}),
    )


def signed_transport(
    payloads: dict[str, Any],
    *,
    token: str = TOKEN,
    status: int = 200,
    seen: list[httpx.Request] | None = None,
) -> httpx.MockTransport:
    def handler(request: httpx.Request) -> httpx.Response:
        if seen is not None:
            seen.append(request)
        payload = payloads.get(request.url.host)
        answer = status if payload is not None else 404
        body = (
            payload if isinstance(payload, bytes) else json.dumps(payload or {"detail": "Not Found"}).encode()
        )
        nonce = request.headers.get("x-cross-portal-nonce", "")
        signature = reference_signature(token, body, method="GET", path=FEED_PATH, nonce=nonce)
        return httpx.Response(answer, content=body, headers={"X-Cross-Portal-Signature": signature})

    return httpx.MockTransport(handler)


def both_portals() -> dict[str, Any]:
    return {"designer.example.com": designer_payload(), "field.example.com": field_payload()}


def edited(payload: dict[str, Any], change: Callable[[dict[str, Any]], None]) -> dict[str, Any]:
    copied = copy.deepcopy(payload)
    change(copied)
    return copied
