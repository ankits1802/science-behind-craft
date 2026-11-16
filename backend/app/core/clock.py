from __future__ import annotations

from zoneinfo import ZoneInfo

__all__ = ["INDIA_TZ", "INDIA_TZ_NAME"]

INDIA_TZ_NAME = "Asia/Kolkata"
INDIA_TZ = ZoneInfo(INDIA_TZ_NAME)
