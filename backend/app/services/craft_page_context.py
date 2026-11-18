from __future__ import annotations

import re
import uuid
from collections.abc import Sequence

from app.research.craft_page import PageClaim, PagePlace
from app.research.craft_page_context import (
    EVENT_KINDS,
    EnvironmentStep,
    PageDepth,
    PageEvent,
    PageGi,
    PageTabs,
    StepPlace,
)
from app.research.craft_page_process import PageProcess
from app.research.stated_dates import states_date
from app.research.timeline import years_offered

from .craft_page_family import depth_basis
from .craft_page_market import GiFacts, MarketFacts
from .craft_page_offers import PageOffers
from .craft_page_parts import Visible
from .curated_index import CuratedPage

__all__ = [
    "page_depth",
    "page_environment",
    "page_events",
    "page_gi",
    "page_tabs",
]

CURATED = "CURATED"
HYPOTHESIS = "HYPOTHESIS"
YEAR_CHARS = 4
NO_RECORD = re.compile(r"\bno\s+(?:records?|examples?|evidence|traces?|mentions?)\b", re.IGNORECASE)


def page_tabs(process: PageProcess, offers: PageOffers, *, sources: bool, evidence: bool) -> PageTabs:
    return PageTabs(
        process=bool(process.stages or process.reactions),
        region=offers.region,
        shared_science=offers.shared_science,
        sources=sources or offers.region_sources,
        evidence=evidence,
    )


def page_depth(
    curated: CuratedPage | None, claims: Sequence[PageClaim], counts: tuple[int, int, int]
) -> PageDepth:
    sources, stages, pictures = counts
    coverage = curated.coverage if curated is not None else None
    return PageDepth(
        basis=depth_basis(coverage, len(claims)),
        coverage=coverage,
        claims=len(claims),
        sources=sources,
        stages=stages,
        pictures=pictures,
    )


def page_gi(status: str | None, gi: GiFacts | None, visible: Visible) -> PageGi:
    claims = visible.keep(gi.claim_ids) if gi is not None else []
    if gi is None or not claims:
        return PageGi(
            status=status,
            application_number=None,
            certificate_number=None,
            filed_on=None,
            registered_on=None,
            journal_issue=None,
            proprietors=[],
            authorised_user_count=None,
            claim_ids=[],
        )
    return PageGi(
        status=status,
        application_number=gi.application_number,
        certificate_number=gi.certificate_number,
        filed_on=gi.filed_on,
        registered_on=gi.registered_on,
        journal_issue=gi.journal_issue,
        proprietors=list(gi.proprietors),
        authorised_user_count=gi.authorised_user_count,
        claim_ids=claims,
    )


def page_events(
    market: MarketFacts, claims: Sequence[PageClaim], visible: Visible, *, curated: bool
) -> list[PageEvent]:
    texts = {claim.id: claim.text for claim in claims}
    events = [*_gi_events(market.gi, texts, visible), *_market_events(market, visible)]
    used = {claim_id for event in events for claim_id in event.claim_ids}
    used |= set(market.gi.claim_ids) if market.gi is not None else set()
    for claim in claims:
        if claim.id in used or not _states_an_event(claim, curated=curated):
            continue
        spans = years_offered([claim.text])
        if spans:
            start, end = min(spans, key=lambda span: (span[0], -span[1]))
            events.append(_event("STATED", (start, end), None, [claim.id]))
    return sorted(
        events,
        key=lambda event: (
            event.start,
            event.end,
            EVENT_KINDS.index(event.kind),
            visible.order[event.claim_ids[0]],
        ),
    )


def page_environment(
    curated: CuratedPage | None, visible: Visible, places: Sequence[PagePlace]
) -> list[EnvironmentStep]:
    if curated is None:
        return []
    names = {place.key: place.name for place in places}
    steps = []
    for item in curated.environment:
        claims = visible.keep(item.claim_ids)
        if claims:
            key = item.place_key
            place = StepPlace(key=key, name=names[key]) if key is not None and key in names else None
            steps.append(EnvironmentStep(factor=item.factor, place=place, claim_ids=claims))
    return steps


def _states_an_event(claim: PageClaim, *, curated: bool) -> bool:
    if claim.level == HYPOTHESIS or (curated and claim.provenance != CURATED):
        return False
    return NO_RECORD.search(claim.text) is None


def _gi_events(gi: GiFacts | None, texts: dict[uuid.UUID, str], visible: Visible) -> list[PageEvent]:
    shown = visible.keep(gi.claim_ids) if gi is not None else []
    if gi is None or not shown:
        return []
    events = []
    for kind, day in (("GI_FILED", gi.filed_on), ("GI_REGISTERED", gi.registered_on)):
        if day is not None:
            stating = [claim_id for claim_id in shown if states_date(day, [texts[claim_id]])]
            events.append(_event(kind, _year_span(day), day, stating or shown))
    return events


def _market_events(market: MarketFacts, visible: Visible) -> list[PageEvent]:
    events = [
        _event(
            "PRICE", _year_span(price.priced_on), price.priced_on, [price.claim_id], place=price.place_name
        )
        for price in market.prices
        if price.claim_id in visible.levels
    ]
    events += [
        _event("WORKFORCE", (entry.year, entry.year), None, [entry.claim_id])
        for entry in market.workforce
        if entry.claim_id in visible.levels
    ]
    return events


def _year_span(day: str) -> tuple[int, int]:
    year = int(day[:YEAR_CHARS])
    return year, year


def _event(
    kind: str, span: tuple[int, int], day: str | None, claim_ids: list[uuid.UUID], *, place: str | None = None
) -> PageEvent:
    return PageEvent(kind=kind, start=span[0], end=span[1], date=day, place=place, claim_ids=claim_ids)
