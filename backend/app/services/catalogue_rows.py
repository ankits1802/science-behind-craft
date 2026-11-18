from __future__ import annotations

import re
import uuid
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field

from app.core.errors import InvalidInput
from app.research.craft_catalogue import (
    CatalogueConcept,
    CatalogueCraft,
    CatalogueDepth,
    CatalogueHero,
    CatalogueSummary,
)
from app.research.media_refs import MediaRef
from app.research.subject_keys import term_key
from app.sources.reference.commons_urls import commons_thumbnail_url

from .craft_page_family import hero_index, masthead_index
from .curated_index import IndexPicture

__all__ = [
    "EMPTY_DEPTH",
    "HERO_THUMB_WIDTH",
    "LOCAL_NAME_SOURCES",
    "NO_EXTRAS",
    "CatalogueExtras",
    "ConceptLink",
    "catalogue_concepts",
    "catalogue_hero",
    "catalogue_summary",
    "curated_hero",
    "is_reader_craft",
    "keys_of",
    "local_name_of",
    "material_link",
]

ACTIVE = "ACTIVE"
GI = "GI"
INLINE = "INLINE"
LATIN_SCRIPT = "Latn"
HERO_THUMB_WIDTH = 500
LOCAL_NAME_SOURCES = ("CURATED", "IMMERSIVE", "WIKIDATA")
EMPTY_DEPTH = CatalogueDepth(coverage=None, claims=0, stages=0, pictures=0, places=0)
GLOSSED_NAME = re.compile(r"^(?P<head>[^()]+?)\s*\((?P<gloss>[^()]+)\)$")
GLOSS_SEPARATOR = re.compile(r"\s*[,;/]\s*")


@dataclass(frozen=True)
class ConceptLink:
    key: str
    label: str
    names: tuple[str, ...]
    craft_id: str


@dataclass(frozen=True)
class CatalogueExtras:
    depth: Mapping[str, CatalogueDepth] = field(default_factory=dict)
    heroes: Mapping[str, CatalogueHero] = field(default_factory=dict)
    gi_years: Mapping[str, int] = field(default_factory=dict)
    located: frozenset[str] = frozenset()
    concepts: tuple[ConceptLink, ...] = ()


NO_EXTRAS = CatalogueExtras()


def is_reader_craft(craft: CatalogueCraft) -> bool:
    return getattr(craft, "status", ACTIVE) == ACTIVE and not craft.is_catch_all


def keys_of(names: Iterable[str]) -> frozenset[str]:
    keys: set[str] = set()
    for name in names:
        try:
            keys.add(term_key(name))
        except InvalidInput:
            continue
    return frozenset(keys)


def material_link(name: str, craft_id: str) -> ConceptLink | None:
    glossed = GLOSSED_NAME.match(name.strip())
    head = glossed["head"].strip() if glossed else name.strip()
    others = tuple(item for item in GLOSS_SEPARATOR.split(glossed["gloss"]) if item) if glossed else ()
    try:
        key = term_key(head)
    except InvalidInput:
        return None
    return ConceptLink(key=key, label=head, names=others, craft_id=craft_id)


def curated_hero(
    pictures: Sequence[IndexPicture], media: Mapping[uuid.UUID, MediaRef]
) -> CatalogueHero | None:
    held = [item for item in pictures if item.media_ref_id in media]
    shown = [(media[item.media_ref_id], item.stage_key) for item in held]
    masthead = masthead_index([item.placement.role if item.placement else None for item in held])
    chosen = hero_index(shown, masthead=masthead)
    return None if chosen is None else catalogue_hero(shown[chosen][0])


def catalogue_hero(media: MediaRef) -> CatalogueHero | None:
    if media.display != INLINE or not media.author:
        return None
    url, width, height = _thumbnail(media)
    return CatalogueHero(
        url=url,
        width=width,
        height=height,
        alt=media.alt,
        author=media.author,
        licence=media.licence,
        licence_url=media.licence_url,
        site=media.site,
        page_url=media.page_url,
    )


def local_name_of(
    states: Sequence[str], aliases: Iterable[Mapping[str, object]], languages: Mapping[str, tuple[str, ...]]
) -> str | None:
    sourced = [row for row in aliases if _sourced_local(row)]
    for state in states:
        for language in languages.get(state, ()):
            spoken = sorted((row for row in sourced if row.get("lang") == language), key=_local_rank)
            if spoken:
                return str(spoken[0]["alias"])
    return None


def catalogue_concepts(
    links: Iterable[ConceptLink], reader_slugs: Mapping[str, str], craft_keys: frozenset[str]
) -> list[CatalogueConcept]:
    labels: dict[str, str] = {}
    names: dict[str, dict[str, None]] = {}
    slugs: dict[str, dict[str, None]] = {}
    for link in links:
        slug = reader_slugs.get(link.craft_id)
        if slug is None or link.key in craft_keys:
            continue
        labels.setdefault(link.key, link.label)
        names.setdefault(link.key, {}).update(dict.fromkeys((link.label, *link.names)))
        slugs.setdefault(link.key, {})[slug] = None
    concepts = [
        CatalogueConcept(
            key=key,
            label=label,
            names=sorted(name for name in names[key] if name != label),
            craft_slugs=sorted(slugs[key]),
        )
        for key, label in labels.items()
    ]
    return sorted(
        concepts, key=lambda concept: (-len(concept.craft_slugs), concept.label.casefold(), concept.key)
    )


def catalogue_summary(
    crafts: Sequence[CatalogueCraft], located: frozenset[str], known_states: frozenset[str]
) -> CatalogueSummary:
    readers = [craft for craft in crafts if is_reader_craft(craft)]
    states = {state for craft in readers for state in craft.state_of_practice if state in known_states}
    placed = [
        craft
        for craft in readers
        if craft.id in located or any(state in known_states for state in craft.state_of_practice)
    ]
    return CatalogueSummary(
        crafts=len(readers),
        gi_registered=sum(craft.gi_status == GI for craft in readers),
        states=len(states),
        placed=len(placed),
        families=len({craft.category_id for craft in readers if craft.category_id}),
        kinds=len({craft.sub_category_id for craft in readers if craft.sub_category_id}),
    )


def _thumbnail(media: MediaRef) -> tuple[str, int | None, int | None]:
    if media.width is None or media.height is None or media.width <= HERO_THUMB_WIDTH:
        return media.image_url, media.width, media.height
    thumb = commons_thumbnail_url(media.image_url, HERO_THUMB_WIDTH)
    if thumb is None:
        return media.image_url, media.width, media.height
    return thumb, HERO_THUMB_WIDTH, max(1, round(media.height * HERO_THUMB_WIDTH / media.width))


def _sourced_local(row: Mapping[str, object]) -> bool:
    return (
        str(row.get("status") or ACTIVE) == ACTIVE
        and row.get("source") in LOCAL_NAME_SOURCES
        and row.get("script") not in (None, LATIN_SCRIPT)
        and bool(row.get("alias"))
    )


def _local_rank(row: Mapping[str, object]) -> tuple[int, int, str]:
    alias = str(row["alias"])
    return LOCAL_NAME_SOURCES.index(str(row["source"])), len(alias), alias
