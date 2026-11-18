from __future__ import annotations

import uuid
from collections import Counter
from collections.abc import Sequence

from app.core.clock import INDIA_TZ
from app.research.citations import Citation, SourceRef
from app.research.craft_masthead import (
    CiteThis,
    Kicker,
    Masthead,
    MastheadGi,
    NativeName,
    Provenance,
    Reliability,
)
from app.research.craft_page import PageDepth, PageEvent, PagePlace
from app.research.craft_parts import PagePlate

from .chapter_context import ChapterContext
from .craft_page_family import family_place

__all__ = ["NEUTRAL_PALETTE", "cite_this", "masthead", "masthead_place"]

NEUTRAL_PALETTE = "paper"
PLACED_ROLES = ("PRACTISED", "ORIGIN")
GI_EVENTS = {"GI_REGISTERED": "REGISTERED", "GI_FILED": "APPLIED"}
SITE = "KalaVigyan"
DOSSIER = "DOSSIER"


def masthead(
    ctx: ChapterContext,
    picture: PagePlate | None,
    found: tuple[PageDepth, Sequence[PageEvent], Sequence[PagePlace]],
) -> Masthead:
    depth, events, places = found
    craft = ctx.records.craft
    family = family_place(craft.category_name, craft.sub_category_name).family
    return Masthead(
        kicker=Kicker(family=craft.family_label, kind=craft.kind_label),
        name=craft.display_name,
        native_name=_native_name(ctx),
        gi=_gi(ctx, events),
        place=masthead_place(ctx, places),
        provenance=_provenance(ctx, depth),
        picture=picture,
        palette=family.palette if family is not None else NEUTRAL_PALETTE,
    )


def masthead_place(ctx: ChapterContext, places: Sequence[PagePlace]) -> str | None:
    for role in PLACED_ROLES:
        for place in places:
            if place.role == role and place.district is not None and place.district.lgd and place.state:
                return f"{place.district.name}, {place.state.name}"
    practice = ctx.records.craft.state_of_practice
    return practice[0] if practice else None


def cite_this(ctx: ChapterContext, place: str | None) -> CiteThis | None:
    craft = ctx.records.craft
    curated = ctx.records.curated
    path = f"/crafts/{craft.slug.lower()}"
    if curated is None:
        version, day = None, None
    else:
        version, day = curated.version, curated.curated_at.astimezone(INDIA_TZ).date().isoformat()
        path = f"{path}/v{version}"
    where = f", {place}" if place else ""
    edition = f" Curated version {version}, {day}." if version else ""
    address = f"{ctx.rows.site.rstrip('/')}{path}"
    text = (
        f"{SITE}. {craft.display_name}{where}: a monograph of the craft and its science.{edition} {address}"
    )
    key = f"kalavigyan-{craft.slug.lower()}" + (f"-v{version}" if version else "")
    bibtex = (
        f"@misc{{{key},\n  title = {{{craft.display_name}}},\n  author = {{{SITE}}},\n"
        + (f"  year = {{{day[:4]}}},\n  note = {{Curated version {version}, {day}}},\n" if day else "")
        + f"  howpublished = {{\\url{{{address}}}}}\n}}"
    )
    return CiteThis(url=path, version=version, curated_on=day, text=text, bibtex=bibtex)


def _native_name(ctx: ChapterContext) -> NativeName | None:
    curated = ctx.records.curated
    for name in curated.native_names if curated else []:
        claim = ctx.claims.get(name.claim_id)
        if claim is not None:
            return NativeName(
                text=name.text,
                lang=name.language,
                script=name.script,
                source_id=claim.citations[0].source_id,
                source_kind=DOSSIER,
                reviewed=True,
            )
    return None


def _gi(ctx: ChapterContext, events: Sequence[PageEvent]) -> MastheadGi | None:
    for kind, status in GI_EVENTS.items():
        event = next((event for event in events if event.kind == kind), None)
        if event is not None:
            return MastheadGi(status=status, on=event.date, citations=_citations(ctx, event.claim_ids))
    if ctx.records.craft.gi_status == "GI":
        return MastheadGi(status="REGISTERED", on=None, citations=[])
    return None


def _citations(ctx: ChapterContext, claim_ids: Sequence[uuid.UUID]) -> list[Citation]:
    found: dict[str, Citation] = {}
    for claim_id in claim_ids:
        found.update((c.id, c) for c in ctx.claims[claim_id].citations)
    return list(found.values())


def _provenance(ctx: ChapterContext, depth: PageDepth) -> Provenance:
    own = _own_sources(ctx)
    counts = Counter(source.reliability for source in own)
    curated = ctx.records.curated
    return Provenance(
        basis=depth.basis,
        sources=len(own),
        reliability=Reliability(a=counts["A"], b=counts["B"], c=counts["C"], d=counts["D"]),
        curated_on=curated.curated_at.astimezone(INDIA_TZ).date().isoformat() if curated else None,
        updated_on=None,
    )


def _own_sources(ctx: ChapterContext) -> list[SourceRef]:
    own = [ctx.claims[claim_id] for claim_id in ctx.own if claim_id in ctx.claims]
    cited = dict.fromkeys(c.source_id for claim in own for c in claim.citations)
    return [ctx.records.sources[source_id] for source_id in cited if source_id in ctx.records.sources]
