from __future__ import annotations

import asyncio
import json
import uuid
from collections import OrderedDict
from dataclasses import dataclass, field
from typing import Any

__all__ = ["KEPT_PAGES_MAX", "PageCache", "PageKey", "ServedPage", "served_content"]

KEPT_PAGES_MAX = 48

PageKey = tuple[uuid.UUID, str]


@dataclass(frozen=True)
class ServedPage:
    content: bytes
    etag: str
    stamp: str

    @property
    def body(self) -> dict[str, Any]:
        found: dict[str, Any] = json.loads(self.content)
        return found


def served_content(body: dict[str, Any]) -> bytes:
    return json.dumps(body, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


@dataclass
class PageCache:
    most: int = KEPT_PAGES_MAX
    _kept: OrderedDict[PageKey, ServedPage] = field(default_factory=OrderedDict)
    _locks: dict[PageKey, asyncio.Lock] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.most < 1:
            raise ValueError(f"a page cache keeps at least one page, not {self.most}")

    def kept(self, key: PageKey, stamp: str) -> ServedPage | None:
        page = self._kept.get(key)
        if page is None or page.stamp != stamp:
            return None
        self._kept.move_to_end(key)
        return page

    def keep(self, key: PageKey, page: ServedPage) -> None:
        self._kept[key] = page
        self._kept.move_to_end(key)
        while len(self._kept) > self.most:
            self._kept.popitem(last=False)

    def lock(self, key: PageKey) -> asyncio.Lock:
        return self._locks.setdefault(key, asyncio.Lock())
