from __future__ import annotations

import uuid
from collections.abc import Iterable, Iterator, Mapping, Sequence
from dataclasses import dataclass, field

from app.data.craft_master_loader import ACTIVE, ALL_INDIA
from app.data.craft_text import core_key, to_latin_spoken
from app.research.crafts import CraftRef

__all__ = [
    "EXACT_SCORES",
    "FAMILY_MAX_CRAFTS",
    "GENERIC_TOKENS",
    "MAX_NGRAM_TOKENS",
    "MAX_REDIRECT_HOPS",
    "MIN_KEY_CHARS",
    "AliasRecord",
    "CraftIndex",
    "CraftRecord",
    "NameEntry",
    "SlugTarget",
    "SpellingRecord",
    "build_index",
    "keys_of",
]

MIN_KEY_CHARS = 4
MAX_NGRAM_TOKENS = 8
MAX_REDIRECT_HOPS = 5
FAMILY_MAX_CRAFTS = 8
EXACT_SCORES: Mapping[str, float] = {
    "EXACT_SLUG": 1.0,
    "EXACT_NAME": 1.0,
    "EXACT_ALIAS": 0.97,
    "MERGED_REDIRECT": 0.97,
    "EXACT_SPELLING": 0.95,
}
GENERIC_TOKENS = frozenset(
    [
        "bamboo",
        "basket",
        "baskets",
        "basketry",
        "block",
        "blocks",
        "brass",
        "cane",
        "carpet",
        "carpets",
        "carved",
        "carving",
        "carvings",
        "casting",
        "clay",
        "cloth",
        "copper",
        "cotton",
        "design",
        "designs",
        "doll",
        "dolls",
        "dye",
        "dyed",
        "dyeing",
        "embroidered",
        "embroidery",
        "fabric",
        "folk",
        "glass",
        "gold",
        "hand",
        "handloom",
        "handmade",
        "items",
        "jewellery",
        "jewelry",
        "lacquer",
        "leather",
        "making",
        "mask",
        "masks",
        "metal",
        "metalware",
        "painted",
        "painting",
        "paintings",
        "paper",
        "pottery",
        "print",
        "printed",
        "printing",
        "products",
        "rugs",
        "sari",
        "saree",
        "sarees",
        "shawl",
        "shawls",
        "silk",
        "silver",
        "stone",
        "terracotta",
        "textile",
        "textiles",
        "toy",
        "toys",
        "traditional",
        "tribal",
        "ware",
        "weave",
        "weaves",
        "weaving",
        "wood",
        "wooden",
        "woodwork",
        "wool",
        "woven",
    ]
)


@dataclass(frozen=True)
class CraftRecord:
    id: uuid.UUID
    slug: str
    name: str
    status: str
    is_catch_all: bool = False
    merged_into: uuid.UUID | None = None
    craft_code: str | None = None
    local_name: str | None = None
    places: tuple[str, ...] = ()


@dataclass(frozen=True)
class AliasRecord:
    craft_id: uuid.UUID
    alias: str


@dataclass(frozen=True)
class SpellingRecord:
    craft_code: str
    spelling: str


@dataclass(frozen=True)
class NameEntry:
    key: str
    label: str
    kind: str
    craft_id: uuid.UUID
    redirected: bool

    @property
    def reason_kind(self) -> str:
        return "MERGED_REDIRECT" if self.redirected else self.kind


@dataclass(frozen=True)
class SlugTarget:
    craft_id: uuid.UUID
    redirected: bool


@dataclass(frozen=True)
class CraftIndex:
    refs: Mapping[uuid.UUID, CraftRef]
    slugs: Mapping[str, SlugTarget]
    entries: Mapping[str, tuple[NameEntry, ...]]
    places: Mapping[str, str]
    craft_places: Mapping[uuid.UUID, frozenset[str]]
    embedded: int = 0
    keys: tuple[str, ...] = field(init=False)
    tokens: Mapping[str, frozenset[uuid.UUID]] = field(init=False)
    max_tokens: int = field(init=False)

    def __post_init__(self) -> None:
        keys = tuple(sorted(self.entries))
        object.__setattr__(self, "keys", keys)
        object.__setattr__(self, "tokens", _token_crafts(self.entries))
        longest = max((len(k.split()) for k in (*keys, *self.places)), default=1)
        object.__setattr__(self, "max_tokens", min(longest, MAX_NGRAM_TOKENS))


def keys_of(text: str) -> set[str]:
    return {key for key in (core_key(text), core_key(to_latin_spoken(text))) if len(key) >= MIN_KEY_CHARS}


def build_index(
    crafts: Sequence[CraftRecord],
    aliases: Iterable[AliasRecord],
    spellings: Iterable[SpellingRecord],
    *,
    embedded: int = 0,
) -> CraftIndex:
    by_id = {c.id: c for c in crafts}
    targets = {c.id: target for c in crafts if (target := _target_of(c, by_id)) is not None}
    refs = {t: _ref(by_id[t]) for t in set(targets.values())}
    slugs = {c.slug: SlugTarget(targets[c.id], targets[c.id] != c.id) for c in crafts if c.id in targets}
    named = [c for c in crafts if c.id in targets and not by_id[targets[c.id]].is_catch_all]
    entries = _name_entries(named, targets, list(aliases), list(spellings))
    craft_places = {
        c.id: frozenset(key for key, _ in _place_labels(c.places))
        for c in crafts
        if targets.get(c.id) == c.id and c.places
    }
    places = {key: label for c in crafts for key, label in _place_labels(c.places)}
    return CraftIndex(refs, slugs, entries, places, craft_places, embedded)


def _target_of(craft: CraftRecord, by_id: Mapping[uuid.UUID, CraftRecord]) -> uuid.UUID | None:
    current: CraftRecord | None = craft
    for _ in range(MAX_REDIRECT_HOPS + 1):
        if current is None:
            return None
        if current.status == ACTIVE:
            return current.id
        if current.merged_into is None:
            return None
        current = by_id.get(current.merged_into)
    return None


def _ref(craft: CraftRecord) -> CraftRef:
    return CraftRef(slug=craft.slug, name=craft.name, path=f"/crafts/{craft.slug}")


def _labelled_names(
    craft: CraftRecord, aliases: Mapping[uuid.UUID, list[str]], spellings: Mapping[str, list[str]]
) -> list[tuple[str, str]]:
    labelled = [(craft.name, "EXACT_NAME")]
    labelled += [(craft.local_name, "EXACT_ALIAS")] if craft.local_name else []
    labelled += [(alias, "EXACT_ALIAS") for alias in aliases.get(craft.id, [])]
    labelled += [(spelling, "EXACT_SPELLING") for spelling in spellings.get(craft.craft_code or "", [])]
    return labelled


def _name_entries(
    crafts: Sequence[CraftRecord],
    targets: Mapping[uuid.UUID, uuid.UUID],
    aliases: Sequence[AliasRecord],
    spellings: Sequence[SpellingRecord],
) -> dict[str, tuple[NameEntry, ...]]:
    alias_by_craft: dict[uuid.UUID, list[str]] = {}
    for row in aliases:
        alias_by_craft.setdefault(row.craft_id, []).append(row.alias)
    spelling_by_code: dict[str, list[str]] = {}
    for row in spellings:
        spelling_by_code.setdefault(row.craft_code, []).append(row.spelling)
    best: dict[tuple[str, uuid.UUID], NameEntry] = {}
    for craft in crafts:
        target = targets[craft.id]
        for label, kind in _labelled_names(craft, alias_by_craft, spelling_by_code):
            for key in keys_of(label):
                entry = NameEntry(key, label, kind, target, target != craft.id)
                held = best.get((key, target))
                if held is None or _entry_rank(entry) < _entry_rank(held):
                    best[(key, target)] = entry
    grouped: dict[str, list[NameEntry]] = {}
    for (key, _), entry in sorted(best.items(), key=lambda item: (item[0][0], str(item[0][1]))):
        grouped.setdefault(key, []).append(entry)
    return {key: tuple(found) for key, found in grouped.items()}


def _entry_rank(entry: NameEntry) -> tuple[float, bool, str]:
    return (-EXACT_SCORES[entry.reason_kind], entry.redirected, entry.label)


def _place_labels(places: Iterable[str]) -> Iterator[tuple[str, str]]:
    for place in places:
        label = (place or "").strip()
        if label and label != ALL_INDIA:
            for key in keys_of(label):
                yield key, label


def _token_crafts(entries: Mapping[str, Sequence[NameEntry]]) -> dict[str, frozenset[uuid.UUID]]:
    found: dict[str, set[uuid.UUID]] = {}
    for key, listed in entries.items():
        for token in key.split():
            if len(token) >= MIN_KEY_CHARS and token not in GENERIC_TOKENS:
                found.setdefault(token, set()).update(entry.craft_id for entry in listed)
    return {token: frozenset(ids) for token, ids in found.items() if len(ids) <= FAMILY_MAX_CRAFTS}
