from __future__ import annotations

from collections.abc import Collection, Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from decimal import Decimal
from functools import lru_cache
from types import MappingProxyType

from app.data.district_register import load_district_codes
from app.research.blocks_insight import MeasureRegion
from app.research.citations import Citation, SourceRef
from app.research.stated_quantities import stated_factors
from app.science.records import KnownClaim

from .stated_names import register_places_named

__all__ = [
    "CraftPlaces",
    "RegionalFactor",
    "RegionalFactors",
    "chosen_factors",
    "claim_factors",
    "district_states",
    "stated_region",
]


@dataclass(frozen=True)
class CraftPlaces:
    states: frozenset[int] = frozenset()
    districts: frozenset[int] = frozenset()


@dataclass(frozen=True)
class RegionalFactor:
    unit: str
    metric_unit: str
    factor: Decimal
    region: MeasureRegion
    citation: Citation


@dataclass(frozen=True)
class RegionalFactors:
    factors: Mapping[str, RegionalFactor] = field(default_factory=dict)
    sources: Mapping[str, SourceRef] = field(default_factory=dict)


@lru_cache(maxsize=1)
def district_states() -> Mapping[int, int]:
    codes = load_district_codes()
    return MappingProxyType(
        {lgd: state for (name, _), lgd in codes.districts.items() if (state := codes.state_lgd(name))}
    )


def stated_region(texts: Sequence[str]) -> MeasureRegion | None:
    codes = load_district_codes()
    names = {name for text in texts for name in register_places_named(text)}
    states = sorted(name for name in names if codes.state_lgd(name) is not None)
    named = [(state, district) for state, district in codes.districts if district in names]
    districts = [pair for pair in named if not states or pair[0] in states]
    if len(districts) == 1:
        state, district = districts[0]
        return MeasureRegion(
            state_lgd=codes.state_lgd(state),
            state_name=state,
            district_lgd=codes.district_lgd(state, district),
            district_name=district,
        )
    if named or len(states) != 1:
        return None
    return MeasureRegion(
        state_lgd=codes.state_lgd(states[0]), state_name=states[0], district_lgd=None, district_name=None
    )


def claim_factors(claim: KnownClaim, units: Collection[str]) -> list[RegionalFactor]:
    found: list[RegionalFactor] = []
    for citation in claim.citations:
        factors = [factor for factor in stated_factors(citation.quote or "") if factor.unit in units]
        region = stated_region([citation.quote or "", claim.text]) if factors else None
        if region is None:
            continue
        found.extend(
            RegionalFactor(factor.unit, factor.metric_unit, factor.factor, region, citation)
            for factor in factors
        )
    return found


def chosen_factors(factors: Iterable[RegionalFactor], places: CraftPlaces) -> dict[str, RegionalFactor]:
    by_unit: dict[str, list[RegionalFactor]] = {}
    for factor in factors:
        if _holds_in(factor.region, places):
            by_unit.setdefault(factor.unit, []).append(factor)
    chosen: dict[str, RegionalFactor] = {}
    for unit, found in by_unit.items():
        narrowest = [factor for factor in found if factor.region.district_lgd is not None] or found
        if len({(factor.factor, factor.metric_unit) for factor in narrowest}) == 1:
            chosen[unit] = narrowest[0]
    return chosen


def _holds_in(region: MeasureRegion, places: CraftPlaces) -> bool:
    if region.district_lgd is not None:
        return region.district_lgd in places.districts
    return region.state_lgd in places.states
