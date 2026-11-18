from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, replace

from .dossier import Dossier
from .limits import (
    CATEGORY_CLAIMS_MAX,
    CATEGORY_CLAIMS_MIN,
    CATEGORY_CORE_DISCIPLINES,
    CATEGORY_SOURCES_MIN,
    CATEGORY_STRONG_SOURCES_MIN,
    CLAIMS_MAX,
    DISCIPLINE_CLAIMS_MIN,
    FULL_CLAIMS_MIN,
    FULL_CORE_DISCIPLINES,
    FULL_FURTHER_DISCIPLINES_MIN,
    FULL_SECTIONS_MIN,
    FULL_SOURCES_MIN,
    FULL_STRONG_SOURCES_MIN,
    STRONG_RELIABILITIES,
    THIN_CLAIMS_MIN,
)
from .problems import Problem
from .vocabulary import CENTRE_ROLES, FAMILY_CENTRE_KINDS, INDIA

__all__ = [
    "SCOPE_TARGETS",
    "Targets",
    "coverage_problems",
    "covered_disciplines",
    "full_shortfalls",
    "thin_shortfalls",
]


@dataclass(frozen=True)
class Targets:
    claims_min: int
    claims_max: int
    sources_min: int
    strong_sources_min: int
    core_disciplines: tuple[str, ...]
    stages: bool
    centre_kinds_without_district: tuple[str, ...]


CRAFT_TARGETS = Targets(
    claims_min=FULL_CLAIMS_MIN,
    claims_max=CLAIMS_MAX,
    sources_min=FULL_SOURCES_MIN,
    strong_sources_min=FULL_STRONG_SOURCES_MIN,
    core_disciplines=FULL_CORE_DISCIPLINES,
    stages=True,
    centre_kinds_without_district=(),
)
SCOPE_TARGETS = {
    "CRAFT": CRAFT_TARGETS,
    "FAMILY": replace(CRAFT_TARGETS, centre_kinds_without_district=FAMILY_CENTRE_KINDS),
    "CATEGORY": Targets(
        claims_min=CATEGORY_CLAIMS_MIN,
        claims_max=CATEGORY_CLAIMS_MAX,
        sources_min=CATEGORY_SOURCES_MIN,
        strong_sources_min=CATEGORY_STRONG_SOURCES_MIN,
        core_disciplines=CATEGORY_CORE_DISCIPLINES,
        stages=False,
        centre_kinds_without_district=FAMILY_CENTRE_KINDS,
    ),
}


def coverage_problems(dossier: Dossier) -> list[Problem]:
    found = []
    claims_max = SCOPE_TARGETS[dossier.scope].claims_max
    if len(dossier.claims) > claims_max:
        found.append(
            Problem(
                "coverage",
                f"{len(dossier.claims)} claims; a {dossier.scope} dossier holds at most {claims_max}",
            )
        )
    full = full_shortfalls(dossier)
    if dossier.coverage == "FULL":
        return found + [Problem("coverage", f"FULL needs {shortfall}") for shortfall in full]
    found += [Problem("coverage", f"THIN needs {shortfall}") for shortfall in thin_shortfalls(dossier)]
    if not full:
        found.append(Problem("coverage", "the dossier meets every FULL target; mark it FULL"))
    return found


def covered_disciplines(dossier: Dossier) -> list[str]:
    counts = Counter(claim.discipline for claim in dossier.claims if not claim.hypothesis)
    return [discipline for discipline, count in counts.items() if count >= DISCIPLINE_CLAIMS_MIN]


def full_shortfalls(dossier: Dossier) -> list[str]:
    targets = SCOPE_TARGETS[dossier.scope]
    shortfalls = _source_shortfalls(dossier, targets)
    if len(dossier.claims) < targets.claims_min:
        shortfalls.append(f"at least {targets.claims_min} claims (has {len(dossier.claims)})")
    shortfalls += _discipline_shortfalls(dossier, targets)
    shortfalls += _place_shortfalls(dossier, targets)
    if targets.stages and not dossier.stages:
        shortfalls.append("the process stages its sources name")
    if len(dossier.overview.sections) < FULL_SECTIONS_MIN:
        shortfalls.append(
            f"at least {FULL_SECTIONS_MIN} overview sections (has {len(dossier.overview.sections)})"
        )
    return shortfalls


def thin_shortfalls(dossier: Dossier) -> list[str]:
    if len(dossier.claims) < THIN_CLAIMS_MIN:
        return [f"at least {THIN_CLAIMS_MIN} claims (has {len(dossier.claims)})"]
    return []


def _source_shortfalls(dossier: Dossier, targets: Targets) -> list[str]:
    shortfalls = []
    if len(dossier.sources) < targets.sources_min:
        shortfalls.append(f"at least {targets.sources_min} sources (has {len(dossier.sources)})")
    strong = sum(1 for source in dossier.sources if source.reliability in STRONG_RELIABILITIES)
    if strong < targets.strong_sources_min:
        shortfalls.append(f"at least {targets.strong_sources_min} sources rated A or B (has {strong})")
    return shortfalls


def _discipline_shortfalls(dossier: Dossier, targets: Targets) -> list[str]:
    covered = covered_disciplines(dossier)
    missing = [discipline for discipline in targets.core_disciplines if discipline not in covered]
    further = [discipline for discipline in covered if discipline not in targets.core_disciplines]
    shortfalls = [f"{DISCIPLINE_CLAIMS_MIN} or more {discipline} claims" for discipline in missing]
    if len(further) < FULL_FURTHER_DISCIPLINES_MIN:
        shortfalls.append(
            f"{FULL_FURTHER_DISCIPLINES_MIN} more disciplines with {DISCIPLINE_CLAIMS_MIN} or more claims "
            f"(has {len(further)})"
        )
    return shortfalls


def _place_shortfalls(dossier: Dossier, targets: Targets) -> list[str]:
    centres = [place for place in dossier.places if place.role in CENTRE_ROLES]
    if not centres:
        return ["a place where the craft is practised"]
    vague = [
        place.id
        for place in centres
        if place.country == INDIA
        and place.district is None
        and place.kind not in targets.centre_kinds_without_district
    ]
    return [f"the district of every centre ({', '.join(vague)} names none)"] if vague else []
