from __future__ import annotations

from functools import cache
from pathlib import Path

__all__ = ["ADMIN_GUIDE_PATH", "ADMIN_GUIDE_TITLE", "ADMIN_GUIDE_URI", "admin_guide"]

ADMIN_GUIDE_PATH = Path(__file__).resolve().parent / "admin" / "published-content.md"
ADMIN_GUIDE_URI = "kalavigyan://admin/published-content.md"
ADMIN_GUIDE_TITLE = "Removing and editing published content"


@cache
def admin_guide() -> str:
    return ADMIN_GUIDE_PATH.read_bytes().decode("utf-8")
