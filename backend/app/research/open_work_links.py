from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from .open_work import Items

__all__ = [
    "ARCHIVED_URL_KEY",
    "DEAD_SOURCE",
    "DEAD_STATUSES",
    "UNARCHIVED_SOURCE",
    "SourceLink",
    "link_state",
    "sources_in_state",
]

ARCHIVED_URL_KEY = "archivedUrl"
DEAD_STATUSES = frozenset({404, 410})
DEAD_SOURCE = "DEAD_SOURCE"
UNARCHIVED_SOURCE = "UNARCHIVED_SOURCE"


@dataclass(frozen=True)
class SourceLink:
    source_id: str
    archived: bool
    last_status: int | None


def link_state(link: SourceLink) -> str | None:
    if link.archived:
        return None
    if link.last_status in DEAD_STATUSES:
        return DEAD_SOURCE
    return UNARCHIVED_SOURCE


def sources_in_state(links: Iterable[SourceLink], state: str) -> Items:
    return Items.of(sorted(link.source_id for link in links if link_state(link) == state))
