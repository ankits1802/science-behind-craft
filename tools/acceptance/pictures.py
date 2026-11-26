from __future__ import annotations

import base64
import re
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

__all__ = ["Picture", "picture_file_name", "reply_pictures"]

EXTENSIONS = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp"}
SLUG_CHARS = 60
NOT_WORD = re.compile(r"[^a-z0-9]+")


@dataclass(frozen=True)
class Picture:
    name: str
    caption: str
    mime: str
    data: bytes


def reply_pictures(content: Sequence[dict[str, Any]]) -> list[Picture]:
    pictures: list[Picture] = []
    caption = ""
    for item in content:
        if item.get("type") == "text":
            caption = str(item.get("text", ""))
            continue
        if item.get("type") != "image":
            continue
        mime = str(item.get("mimeType"))
        data = base64.b64decode(item.get("data", ""), validate=True)
        pictures.append(Picture(picture_file_name(len(pictures) + 1, caption, mime), caption, mime, data))
        caption = ""
    return pictures


def picture_file_name(number: int, caption: str, mime: str) -> str:
    extension = EXTENSIONS.get(mime)
    if extension is None:
        raise ValueError(
            f"the preview returned a picture of type {mime}; expected one of {sorted(EXTENSIONS)}"
        )
    slug = NOT_WORD.sub("-", caption.lower()).strip("-")[:SLUG_CHARS].rstrip("-") or "picture"
    return f"{number:02d}-{slug}.{extension}"
