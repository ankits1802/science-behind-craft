from __future__ import annotations

import logging
import re
from collections.abc import Sequence

from app.research.crafts import CraftRef
from app.research.evidence import SEARCH_QUERY_MAX_CHARS, SearchQuery, personal_data_in
from app.research.planning import (
    MODE_POLICIES,
    FacetCoverage,
    PlannedQuery,
    PlanRequest,
    RetrievalPlan,
)
from app.research.vocabulary import RETRIEVAL_TIERS, STORED_TIERS

from .drafting import DraftQuery, PlanDraft
from .policy import DEGRADED_MODES

__all__ = ["DEFAULT_QUERY_TIER", "effective_mode", "open_facets", "planned_queries", "retrieval_plan"]

logger = logging.getLogger(__name__)

DEFAULT_QUERY_TIER = "T3"
ANCHOR_MIN_CHARS = 3
WORD = re.compile(r"[^\W_]+")


def effective_mode(mode: str, *, degraded: bool) -> str:
    return DEGRADED_MODES.get(mode, mode) if degraded else mode


def open_facets(mode: str, coverage: Sequence[FacetCoverage]) -> list[int]:
    policy = MODE_POLICIES[mode]
    if not policy.max_queries:
        return []
    return [
        entry.facet_index for entry in coverage if not (policy.live_only_for_open_facets and entry.covered)
    ]


def retrieval_plan(
    request: PlanRequest, draft: PlanDraft, coverage: Sequence[FacetCoverage], *, mode: str
) -> RetrievalPlan:
    policy = MODE_POLICIES[mode]
    queries = planned_queries(request, draft, open_facets(mode, coverage), limit=policy.max_queries)
    live_tiers = {query.tier for query in queries}
    return RetrievalPlan(
        mode=mode,
        craft=request.craft,
        intent=draft.intent,
        language=request.language,
        needs_region=draft.needs_region,
        facets=draft.facets,
        tiers=[
            tier
            for tier in RETRIEVAL_TIERS
            if tier in policy.tiers and (tier in STORED_TIERS or tier in live_tiers)
        ],
        queries=queries,
        max_fetches=policy.max_fetches if queries else 0,
    )


def planned_queries(
    request: PlanRequest, draft: PlanDraft, facet_indexes: Sequence[int], *, limit: int
) -> list[PlannedQuery]:
    wanted = set(facet_indexes)
    drafted = [query for query in draft.queries if query.facet_index in wanted]
    firsts = [_first_query(request.craft, draft, drafted, index) for index in facet_indexes]
    ordered = [*firsts, *(query for query in drafted if query not in firsts)]
    planned: list[PlannedQuery] = []
    seen: set[tuple[str, str]] = set()
    for query in ordered:
        search = search_query(query.text, request.craft, withheld=request.withheld_terms)
        key = (query.tier, search.text.casefold()) if search else None
        if search is None or key in seen:
            continue
        seen.add(key)
        planned.append(PlannedQuery(tier=query.tier, facet_index=query.facet_index, query=search))
    return planned[:limit]


def search_query(text: str, craft: CraftRef, *, withheld: Sequence[str]) -> SearchQuery | None:
    anchored = _anchored(text, craft)
    if personal_data_in(anchored):
        logger.warning("left out a planned query that carried personal data")
        return None
    if any(_mentions(anchored, term) for term in withheld):
        logger.warning("left out a planned query that named a withheld term")
        return None
    return SearchQuery(text=anchored)


def _first_query(craft: CraftRef, draft: PlanDraft, drafted: Sequence[DraftQuery], index: int) -> DraftQuery:
    for query in drafted:
        if query.facet_index == index:
            return query
    target = draft.facets[index].target
    return DraftQuery(facet_index=index, tier=DEFAULT_QUERY_TIER, text=f"{craft.name} {target}")


def _anchored(text: str, craft: CraftRef) -> str:
    words = {word.casefold() for word in WORD.findall(text)}
    anchors = {word.casefold() for word in WORD.findall(craft.name) if len(word) >= ANCHOR_MIN_CHARS}
    if not anchors or words & anchors:
        return text[:SEARCH_QUERY_MAX_CHARS].strip()
    return f"{craft.name} {text}"[:SEARCH_QUERY_MAX_CHARS].strip()


def _mentions(text: str, term: str) -> bool:
    return re.search(rf"(?<!\w){re.escape(term.casefold())}(?!\w)", text.casefold()) is not None
