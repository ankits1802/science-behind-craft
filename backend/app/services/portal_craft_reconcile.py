from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field, replace
from typing import Any

from app.core.errors import InvalidInput
from app.data.craft_master_loader import MERGED, normalise, seed_uuid
from app.data.craft_text import alias_lang, alias_norm, script_of
from app.services.portal_craft_feed import (
    DESIGNER,
    FIELD_REPOSITORY,
    PORTALS,
    FeedCode,
    FeedCraft,
    FeedSpelling,
    PortalCraftFeed,
)
from app.services.portal_craft_plan import (
    ORIGIN_KEY,
    SOURCES_KEY,
    CategoryWrite,
    CraftWrite,
    KnownCraft,
    KnownState,
    SubCategoryWrite,
    TaxonomyPlan,
    columns_of,
    combined_status,
    new_codes,
    new_spellings,
    ordered_feeds,
    plan_taxonomy,
    source_record,
)

__all__ = ["ALIAS_SOURCE_BY_PORTAL", "AliasWrite", "Placement", "SyncPlan", "place_crafts", "plan_sync"]

ALIAS_SOURCE_BY_PORTAL = {DESIGNER: "DR_SYNC", FIELD_REPOSITORY: "FR_SYNC"}


@dataclass(frozen=True)
class AliasWrite:
    craft_slug: str
    alias: str
    alias_norm: str
    script: str
    lang: str | None
    source: str


@dataclass(frozen=True)
class SyncPlan:
    portals: tuple[str, ...]
    categories: tuple[CategoryWrite, ...]
    sub_categories: tuple[SubCategoryWrite, ...]
    codes: tuple[FeedCode, ...]
    spellings: tuple[FeedSpelling, ...]
    crafts: tuple[CraftWrite, ...]
    aliases: tuple[AliasWrite, ...]
    name_conflicts: tuple[str, ...]


@dataclass
class Placement:
    kv_slug_of: dict[tuple[str, str], str] = field(default_factory=dict)
    listings: dict[str, dict[str, FeedCraft]] = field(default_factory=dict)


@dataclass
class _Run:
    portals: frozenset[str]
    known: dict[str, KnownCraft]
    master_slugs: frozenset[str]
    taxonomy: TaxonomyPlan
    placement: Placement
    synced_at: str
    names: dict[tuple[str | None, str], str]
    conflicts: list[str] = field(default_factory=list)


def plan_sync(feeds: Sequence[PortalCraftFeed], known: KnownState, *, synced_at: str) -> SyncPlan:
    ordered = ordered_feeds(feeds)
    _refuse_missing_master(known)
    taxonomy = plan_taxonomy(ordered, known)
    run = _Run(
        portals=frozenset(feed.portal for feed in ordered),
        known={craft.slug: craft for craft in known.crafts},
        master_slugs=known.master_slugs,
        taxonomy=taxonomy,
        placement=place_crafts(ordered, known, taxonomy),
        synced_at=synced_at,
        names={(craft.sub_category_slug, craft.name): craft.slug for craft in known.crafts},
    )
    writes = _resolve_merges([_craft_write(run, slug) for slug in _touched(run)], known)
    return SyncPlan(
        portals=tuple(feed.portal for feed in ordered),
        categories=tuple(taxonomy.categories),
        sub_categories=tuple(taxonomy.sub_categories),
        codes=tuple(new_codes(ordered, known)),
        spellings=tuple(new_spellings(ordered, known)),
        crafts=tuple(writes),
        aliases=tuple(_alias_writes(ordered, run.placement, _final_names(known, writes))),
        name_conflicts=tuple(run.conflicts),
    )


def place_crafts(feeds: Sequence[PortalCraftFeed], known: KnownState, taxonomy: TaxonomyPlan) -> Placement:
    placement = Placement()
    slugs = {craft.slug for craft in known.crafts}
    by_name: dict[tuple[str | None, str], str] = {}
    for craft in sorted(known.crafts, key=lambda c: (c.status == MERGED, c.slug)):
        by_name.setdefault((craft.sub_category_slug, normalise(craft.name)), craft.slug)
    for feed in feeds:
        for craft in sorted(feed.crafts, key=lambda c: c.slug):
            sub = taxonomy.sub_slug_of.get((feed.portal, craft.sub_category_id or ""))
            key = (sub, normalise(craft.name))
            slug = craft.slug if craft.slug in slugs else by_name.get(key)
            if slug is None:
                slug = craft.slug
                slugs.add(slug)
                by_name.setdefault(key, slug)
            placement.kv_slug_of[(feed.portal, craft.id)] = slug
            placement.listings.setdefault(slug, {}).setdefault(feed.portal, craft)
    return placement


def _refuse_missing_master(known: KnownState) -> None:
    stored = {craft.slug for craft in known.crafts}
    missing = sorted(known.master_slugs - stored)
    if missing:
        raise InvalidInput(
            f"{len(missing)} master crafts are not stored (first: {missing[0]}); run seed_crafts before the portal sync"
        )


def _touched(run: _Run) -> list[str]:
    dropped = [
        slug
        for slug, craft in sorted(run.known.items())
        if slug not in run.placement.listings and run.portals & set(craft.meta.get(SOURCES_KEY) or {})
    ]
    return [*run.placement.listings, *dropped]


def _craft_write(run: _Run, slug: str) -> CraftWrite:
    stored = run.known.get(slug)
    listed = run.placement.listings.get(slug, {})
    meta: dict[str, Any] = dict(stored.meta) if stored else {}
    meta[SOURCES_KEY] = _sources(run, slug, meta.get(SOURCES_KEY), listed)
    if slug in run.master_slugs:
        return CraftWrite(
            id=seed_uuid("c", slug),
            slug=slug,
            insert=False,
            columns=None,
            status=None,
            merged_into_slug=None,
            meta=meta,
        )
    origin = meta.get(ORIGIN_KEY) or next((portal for portal in PORTALS if portal in listed), None)
    if origin is not None:
        meta[ORIGIN_KEY] = origin
    owner = listed.get(origin) if origin else None
    columns = None
    if owner is not None:
        sub = run.taxonomy.sub_slug_of.get((origin, owner.sub_category_id or ""))
        columns = columns_of(owner, sub_slug=sub, category=run.taxonomy.category_name_of_sub.get(sub or ""))
        renamed_onto_another = not _claim_name(run, slug, stored, (sub, owner.name))
        if renamed_onto_another and stored is not None:
            columns = None
    status, target = combined_status(meta[SOURCES_KEY])
    return CraftWrite(
        id=seed_uuid("c", slug),
        slug=slug,
        insert=stored is None,
        columns=columns,
        status=status,
        merged_into_slug=target,
        meta=meta,
    )


def _sources(run: _Run, slug: str, stored: Any, listed: dict[str, FeedCraft]) -> dict[str, Any]:
    kept = {p: r for p, r in (stored or {}).items() if p in PORTALS and p not in run.portals}
    for portal, craft in listed.items():
        target = run.placement.kv_slug_of.get((portal, craft.merged_into_id or ""))
        kept[portal] = source_record(
            craft, merged_into_slug=None if target == slug else target, synced_at=run.synced_at
        )
    return {portal: kept[portal] for portal in PORTALS if portal in kept}


def _claim_name(run: _Run, slug: str, stored: KnownCraft | None, key: tuple[str | None, str]) -> bool:
    holder = run.names.get(key)
    if holder not in (None, slug):
        run.conflicts.append(f"{slug}: {key[1]!r} is already the name of {holder}")
        return False
    if stored is not None and run.names.get((stored.sub_category_slug, stored.name)) == slug:
        del run.names[(stored.sub_category_slug, stored.name)]
    run.names[key] = slug
    return True


def _resolve_merges(writes: list[CraftWrite], known: KnownState) -> list[CraftWrite]:
    state = {craft.slug: (craft.status, craft.merged_into_slug) for craft in known.crafts}
    for write in writes:
        if write.status is not None:
            state[write.slug] = (write.status, write.merged_into_slug)
    return [
        replace(write, merged_into_slug=_terminal(write.slug, state)) if write.status == MERGED else write
        for write in writes
    ]


def _terminal(slug: str, state: dict[str, tuple[str, str | None]]) -> str:
    seen = {slug}
    current = state[slug][1]
    while True:
        if current is None or current not in state:
            raise InvalidInput(f"craft {slug} is merged into {current!r}, which is not a stored craft")
        status, following = state[current]
        if status != MERGED:
            return current
        if following in seen:
            raise InvalidInput(f"craft {slug} is merged in a loop through {current}")
        seen.add(current)
        current = following


def _final_names(known: KnownState, writes: list[CraftWrite]) -> dict[str, str]:
    names = {craft.slug: craft.name for craft in known.crafts}
    for write in writes:
        if write.columns is not None:
            names[write.slug] = write.columns.name
    return names


def _alias_writes(
    feeds: Sequence[PortalCraftFeed], placement: Placement, names: dict[str, str]
) -> list[AliasWrite]:
    out: list[AliasWrite] = []
    seen: set[tuple[str, str]] = set()
    for feed in feeds:
        source = ALIAS_SOURCE_BY_PORTAL[feed.portal]
        for craft in sorted(feed.crafts, key=lambda c: c.slug):
            slug = placement.kv_slug_of[(feed.portal, craft.id)]
            own = alias_norm(names[slug])
            for text in (craft.name, craft.local_name, *craft.aliases):
                alias = " ".join((text or "").split())
                norm = alias_norm(alias)
                if not norm or norm == own or (slug, norm) in seen:
                    continue
                seen.add((slug, norm))
                out.append(AliasWrite(slug, alias, norm, script_of(alias), alias_lang(alias), source))
    return out
