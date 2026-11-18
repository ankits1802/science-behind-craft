from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace

from app.data.craft_master_loader import ACTIVE, load_master
from app.data.district_register import load_district_codes
from app.data.portal_craft_register import load_portal_crafts
from app.research.craft_page_context import PageRelative
from app.research.crafts import CraftRef

from .craft_page_family import FamilyCandidate, RelativeExtras, page_relative, ranked_family, relative_extras
from .craft_page_market import market_from_rows
from .craft_page_offers import PageOffers
from .craft_page_records import CraftPageRecords
from .curation_plan import CurationPlan

__all__ = [
    "RegisterCraft",
    "register_context",
    "register_craft",
    "register_crafts",
    "register_offers",
    "register_relatives",
]


@dataclass(frozen=True)
class RegisterCraft:
    slug: str
    name: str
    sub_category_slug: str | None
    gi_status: str | None
    state_of_practice: tuple[str, ...]
    catch_all: bool


def register_crafts() -> tuple[RegisterCraft, ...]:
    listed = [
        RegisterCraft(
            craft.slug,
            craft.name,
            craft.sub_category_slug,
            craft.gi_status,
            craft.state_of_practice,
            craft.is_catch_all,
        )
        for craft in load_master()
    ]
    listed += [
        RegisterCraft(
            craft.slug, craft.name, craft.sub_category_slug, craft.gi_status, craft.state_of_practice, False
        )
        for craft in load_portal_crafts()
        if craft.status == ACTIVE
    ]
    return tuple(listed)


def register_craft(slug: str) -> RegisterCraft | None:
    return next((craft for craft in register_crafts() if craft.slug == slug), None)


def register_relatives(slug: str, curated: Mapping[str, CraftPageRecords]) -> tuple[PageRelative, ...]:
    own = register_craft(slug)
    if own is None or own.sub_category_slug is None:
        return ()
    family = [craft for craft in register_crafts() if craft.sub_category_slug == own.sub_category_slug]
    chosen = ranked_family([_candidate(craft, curated.get(craft.slug)) for craft in family], own_slug=slug)
    return tuple(page_relative(item, _extras(curated.get(item.craft.slug))) for item in chosen)


def register_offers(practice: Sequence[str], locations: Sequence[Mapping[str, object]]) -> PageOffers:
    known = {name.casefold() for name in load_district_codes().states}
    practised = any(state.strip().casefold() in known for state in practice)
    return PageOffers(
        region=bool(locations) or practised,
        region_sources=any(row.get("sourceId") for row in locations),
        shared_science=False,
    )


def register_context(
    records: CraftPageRecords,
    plan: CurationPlan | None,
    curated: Mapping[str, CraftPageRecords],
) -> CraftPageRecords:
    slug = records.craft.slug
    found = register_craft(slug)
    if plan is not None:
        records = replace(
            records,
            market=market_from_rows(plan.part("giRecords"), plan.part("prices"), plan.part("workforce")),
        )
    locations = plan.part("locations") if plan is not None else ()
    return replace(
        records,
        relatives=register_relatives(slug, curated),
        offers=register_offers(records.craft.state_of_practice, locations),
        catch_all=found.catch_all if found is not None else False,
    )


def _candidate(craft: RegisterCraft, records: CraftPageRecords | None) -> FamilyCandidate:
    return FamilyCandidate(
        craft=CraftRef(slug=craft.slug, name=craft.name, path=f"/crafts/{craft.slug}"),
        gi_status=craft.gi_status,
        state_of_practice=craft.state_of_practice,
        coverage=records.curated.coverage if records is not None and records.curated is not None else None,
        claims=len(records.views) if records is not None else 0,
        catch_all=craft.catch_all,
    )


def _extras(records: CraftPageRecords | None) -> RelativeExtras | None:
    if records is None or records.curated is None:
        return None
    lede_id = records.curated.overview.lede_piece_id
    lede = records.pieces.get(lede_id) if lede_id is not None else None
    visible = {view.id for view in records.views}
    return relative_extras(records.curated, records.media, lede, (visible, records.sources))
