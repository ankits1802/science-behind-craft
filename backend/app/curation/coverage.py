from __future__ import annotations

from collections import Counter

from .dossier import Dossier
from .limits import (
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
from .vocabulary import CENTRE_ROLES, INDIA

__all__ = ["coverage_problems", "covered_disciplines", "full_shortfalls", "thin_shortfalls"]


def coverage_problems(dossier: Dossier) -> list[Problem]:
    found = []
    if len(dossier.claims) > CLAIMS_MAX:
        found.append(
            Problem("coverage", f"{len(dossier.claims)} claims; a dossier holds at most {CLAIMS_MAX}")
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
    shortfalls = _source_shortfalls(dossier)
    if len(dossier.claims) < FULL_CLAIMS_MIN:
        shortfalls.append(f"at least {FULL_CLAIMS_MIN} claims (has {len(dossier.claims)})")
    shortfalls += _discipline_shortfalls(dossier)
    shortfalls += _place_shortfalls(dossier)
    if not dossier.stages:
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


def _source_shortfalls(dossier: Dossier) -> list[str]:
    shortfalls = []
    if len(dossier.sources) < FULL_SOURCES_MIN:
        shortfalls.append(f"at least {FULL_SOURCES_MIN} sources (has {len(dossier.sources)})")
    strong = sum(1 for source in dossier.sources if source.reliability in STRONG_RELIABILITIES)
    if strong < FULL_STRONG_SOURCES_MIN:
        shortfalls.append(f"at least {FULL_STRONG_SOURCES_MIN} sources rated A or B (has {strong})")
    return shortfalls


def _discipline_shortfalls(dossier: Dossier) -> list[str]:
    covered = covered_disciplines(dossier)
    missing = [discipline for discipline in FULL_CORE_DISCIPLINES if discipline not in covered]
    further = [discipline for discipline in covered if discipline not in FULL_CORE_DISCIPLINES]
    shortfalls = [f"{DISCIPLINE_CLAIMS_MIN} or more {discipline} claims" for discipline in missing]
    if len(further) < FULL_FURTHER_DISCIPLINES_MIN:
        shortfalls.append(
            f"{FULL_FURTHER_DISCIPLINES_MIN} more disciplines with {DISCIPLINE_CLAIMS_MIN} or more claims "
            f"(has {len(further)})"
        )
    return shortfalls


def _place_shortfalls(dossier: Dossier) -> list[str]:
    centres = [place for place in dossier.places if place.role in CENTRE_ROLES]
    if not centres:
        return ["a place where the craft is practised"]
    vague = [place.id for place in centres if place.country == INDIA and place.district is None]
    return [f"the district of every centre ({', '.join(vague)} names none)"] if vague else []
