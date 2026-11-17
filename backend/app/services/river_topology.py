from __future__ import annotations

import hashlib
import logging
from collections import OrderedDict
from dataclasses import dataclass
from typing import Protocol

from .naming import river_topology_key
from .river_store import BasinFile

__all__ = [
    "TOPOLOGY_CACHE_BYTES",
    "TOPOLOGY_TYPE",
    "TopologyCache",
    "TopologyFile",
    "TopologyObjects",
    "basin_topology",
]

logger = logging.getLogger(__name__)

TOPOLOGY_TYPE = "application/json"
TOPOLOGY_CACHE_BYTES = 48 * 1024 * 1024


class TopologyObjects(Protocol):
    async def get(self, key: str) -> bytes | None: ...


@dataclass(frozen=True)
class TopologyFile:
    body: bytes
    sha256: str


class TopologyCache:
    def __init__(self, *, max_bytes: int = TOPOLOGY_CACHE_BYTES) -> None:
        self.max_bytes = max_bytes
        self._bodies: OrderedDict[str, bytes] = OrderedDict()
        self._held = 0

    def get(self, sha256: str) -> bytes | None:
        body = self._bodies.get(sha256)
        if body is not None:
            self._bodies.move_to_end(sha256)
        return body

    def put(self, sha256: str, body: bytes) -> None:
        if len(body) > self.max_bytes or sha256 in self._bodies:
            return
        self._bodies[sha256] = body
        self._held += len(body)
        while self._held > self.max_bytes:
            _, dropped = self._bodies.popitem(last=False)
            self._held -= len(dropped)


async def basin_topology(
    objects: TopologyObjects, cache: TopologyCache, basin: BasinFile
) -> TopologyFile | None:
    kept = cache.get(basin.sha256)
    if kept is not None:
        return TopologyFile(body=kept, sha256=basin.sha256)
    body = await objects.get(river_topology_key(basin.edition, basin.main_riv, basin.sha256))
    if body is None:
        logger.error("river %s has a stored basin but no topology file", basin.main_riv)
        return None
    found = hashlib.sha256(body).hexdigest()
    if found != basin.sha256:
        logger.error(
            "river %s's topology file is %s, the load stored %s; it is not served",
            basin.main_riv,
            found,
            basin.sha256,
        )
        return None
    cache.put(found, body)
    return TopologyFile(body=body, sha256=found)
