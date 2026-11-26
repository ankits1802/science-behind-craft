from __future__ import annotations

import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from functools import lru_cache
from typing import Any

from .river_names import RIVER_NAMES_DIR

__all__ = [
    "RIVER_ALIASES_CODE",
    "RIVER_ALIASES_FILE",
    "RIVER_ALIASES_SCHEMA_VERSION",
    "AliasSource",
    "RiverAlias",
    "load_river_aliases",
    "parse_river_aliases",
]

RIVER_ALIASES_FILE = RIVER_NAMES_DIR / "river_aliases.json"
RIVER_ALIASES_SCHEMA_VERSION = 1
RIVER_ALIASES_CODE = "RIVER_ALIASES"
NAMES_MIN = 2
GRADES = frozenset({"A", "B", "C", "D"})
ALIAS_ID = re.compile(r"^[a-z][a-z0-9-]{0,59}$")
READ_ON = re.compile(r"^\d{4}-\d{2}-\d{2}$")
HTTPS = "https://"
NO_SOURCE = (
    "the river alias {id!r} cites no source: an alias is recorded only with a source whose quote names "
    "its rivers as one"
)
UNSTATED = "the river alias {id!r} names {name!r}, which no quote of its sources states"
ONE_NAME = (
    "a source of the river alias {id!r} quotes {count} of its names; a quote that states the alias names two"
)


@dataclass(frozen=True)
class AliasSource:
    title: str
    authors: tuple[str, ...]
    publisher: str
    year: int
    url: str
    doi: str | None
    grade: str
    quote: str
    locator: str
    retrieved_at: str


@dataclass(frozen=True)
class RiverAlias:
    id: str
    names: tuple[str, ...]
    district_lgds: frozenset[int]
    sources: tuple[AliasSource, ...]

    @property
    def ref(self) -> str:
        return f"{RIVER_ALIASES_CODE}:{self.id}"


def parse_river_aliases(body: Mapping[str, Any]) -> tuple[RiverAlias, ...]:
    if body.get("schemaVersion") != RIVER_ALIASES_SCHEMA_VERSION:
        raise ValueError(f"the river aliases file is schema version {RIVER_ALIASES_SCHEMA_VERSION}")
    if body.get("register", {}).get("code") != RIVER_ALIASES_CODE:
        raise ValueError(f"the river aliases file is the register {RIVER_ALIASES_CODE}")
    aliases = tuple(_alias(row) for row in body["aliases"])
    ids = [alias.id for alias in aliases]
    if len(set(ids)) != len(ids):
        raise ValueError("each river alias has an id of its own")
    return aliases


@lru_cache(maxsize=1)
def load_river_aliases() -> tuple[RiverAlias, ...]:
    return parse_river_aliases(json.loads(RIVER_ALIASES_FILE.read_text(encoding="utf-8")))


def _alias(row: Mapping[str, Any]) -> RiverAlias:
    alias_id = str(row.get("id", ""))
    if not ALIAS_ID.match(alias_id):
        raise ValueError(f"a river alias's id {alias_id!r} is lower case letters, digits and hyphens")
    names = tuple(dict.fromkeys(str(name).strip() for name in row.get("names") or [] if str(name).strip()))
    if len(names) < NAMES_MIN:
        raise ValueError(f"the river alias {alias_id!r} names at least {NAMES_MIN} rivers as one")
    districts = frozenset(int(lgd) for lgd in row.get("districtLgds") or [])
    if not districts:
        raise ValueError(f"the river alias {alias_id!r} names the districts its river crosses")
    sources = tuple(_source(alias_id, source) for source in row.get("sources") or [])
    if not sources:
        raise ValueError(NO_SOURCE.format(id=alias_id))
    _stated(alias_id, names, sources)
    return RiverAlias(id=alias_id, names=names, district_lgds=districts, sources=sources)


def _source(alias_id: str, row: Mapping[str, Any]) -> AliasSource:
    url, grade, read_on = str(row.get("url", "")), str(row.get("grade", "")), str(row.get("retrievedAt", ""))
    if not url.startswith(HTTPS):
        raise ValueError(f"a source of the river alias {alias_id!r} is read over https")
    if grade not in GRADES or not READ_ON.match(read_on):
        raise ValueError(
            f"a source of the river alias {alias_id!r} carries its grade and the day it was read"
        )
    texts = {key: str(row.get(key) or "").strip() for key in ("title", "publisher", "quote", "locator")}
    missing = sorted(key for key, value in texts.items() if not value)
    if missing:
        raise ValueError(f"a source of the river alias {alias_id!r} gives no {', '.join(missing)}")
    doi = row.get("doi")
    return AliasSource(
        title=texts["title"],
        authors=tuple(str(author) for author in row.get("authors") or []),
        publisher=texts["publisher"],
        year=int(row["year"]),
        url=url,
        doi=str(doi) if doi else None,
        grade=grade,
        quote=texts["quote"],
        locator=texts["locator"],
        retrieved_at=read_on,
    )


def _stated(alias_id: str, names: Sequence[str], sources: Sequence[AliasSource]) -> None:
    quotes = [source.quote.casefold() for source in sources]
    for quote in quotes:
        count = sum(name.casefold() in quote for name in names)
        if count < NAMES_MIN:
            raise ValueError(ONE_NAME.format(id=alias_id, count=count))
    for name in names:
        if not any(name.casefold() in quote for quote in quotes):
            raise ValueError(UNSTATED.format(id=alias_id, name=name))
