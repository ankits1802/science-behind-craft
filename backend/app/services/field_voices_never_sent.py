from __future__ import annotations

import re
from collections.abc import Iterator
from typing import Any

__all__ = ["FORBIDDEN_KEYS", "FORBIDDEN_KEY_PARTS", "forbidden_keys"]

FORBIDDEN_KEYS = frozenset(
    {
        "accuracy",
        "age",
        "agegroup",
        "ageyears",
        "altitude",
        "coordinates",
        "dob",
        "gender",
        "geo",
        "geolocation",
        "gps",
        "lat",
        "lng",
        "locality",
        "lon",
        "long",
        "mobile",
        "place",
        "placename",
        "village",
        "whatsapp",
    }
)
FORBIDDEN_KEY_PARTS = (
    "phone",
    "email",
    "aadhaar",
    "pehchan",
    "fingerprint",
    "birth",
    "address",
    "pincode",
    "postcode",
    "latitude",
    "longitude",
)
KEY_NOISE = re.compile(r"[^a-z0-9]")


def forbidden_keys(payload: Any) -> list[str]:
    found: list[str] = []
    for path, key in _keys(payload):
        normal = KEY_NOISE.sub("", key.lower())
        if normal in FORBIDDEN_KEYS or any(part in normal for part in FORBIDDEN_KEY_PARTS):
            found.append(f"{path}.{key}" if path else key)
    return found


def _keys(payload: Any) -> Iterator[tuple[str, str]]:
    stack: list[tuple[str, Any]] = [("", payload)]
    while stack:
        path, value = stack.pop()
        if isinstance(value, list):
            stack.extend((f"{path}[{index}]", item) for index, item in enumerate(value))
        elif isinstance(value, dict):
            for key, item in value.items():
                yield path, str(key)
                stack.append((f"{path}.{key}" if path else str(key), item))
