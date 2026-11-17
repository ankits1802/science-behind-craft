from __future__ import annotations

import json
from collections import Counter
from collections.abc import Iterable
from typing import Literal
from urllib.parse import urlsplit

from pydantic import AwareDatetime, Field

from app.models.enums import DISCIPLINES, RELIABILITIES
from app.research.base import ContractModel

from .dossier import Dossier
from .files import DossierResult
from .parts import Claim
from .vocabulary import CoverageClass

__all__ = [
    "CHECK_STATUSES",
    "INDEX_SCHEMA_VERSION",
    "CurationIndex",
    "IndexCheck",
    "IndexEntry",
    "corroborated",
    "curation_index",
    "index_text",
    "part_counts",
]

INDEX_SCHEMA_VERSION = 1
CHECK_STATUSES = ("PASS", "FAIL")
CORROBORATING_PUBLISHERS_MIN = 2


class IndexCheck(ContractModel):
    status: Literal[*CHECK_STATUSES]
    problems: int = Field(ge=0)
    verified_at: AwareDatetime | None = None


class IndexEntry(ContractModel):
    craft_slug: str
    file: str
    version: int | None = None
    coverage: CoverageClass | None = None
    curated_at: AwareDatetime | None = None
    counts: dict[str, int] = Field(default_factory=dict)
    claims_by_discipline: dict[str, int] = Field(default_factory=dict)
    sources_by_reliability: dict[str, int] = Field(default_factory=dict)
    check: IndexCheck


class CurationIndex(ContractModel):
    schema_version: Literal[1] = INDEX_SCHEMA_VERSION
    crafts: list[IndexEntry]


def curation_index(results: Iterable[DossierResult]) -> CurationIndex:
    entries = [_entry(result) for result in results]
    return CurationIndex(crafts=sorted(entries, key=lambda entry: (entry.craft_slug, entry.file)))


def index_text(index: CurationIndex) -> str:
    return json.dumps(index.model_dump(mode="json", by_alias=True), indent=2, ensure_ascii=False) + "\n"


def corroborated(dossier: Dossier, claim: Claim) -> bool:
    publishers = {_publisher(dossier, quote.source_id) for quote in claim.quotes}
    return len(publishers) >= CORROBORATING_PUBLISHERS_MIN


def part_counts(dossier: Dossier) -> dict[str, int]:
    return {
        "sources": len(dossier.sources),
        "claims": len(dossier.claims),
        "hypotheses": sum(1 for claim in dossier.claims if claim.hypothesis),
        "corroborated": sum(1 for claim in dossier.claims if corroborated(dossier, claim)),
        "places": len(dossier.places),
        "communities": len(dossier.communities),
        "stages": len(dossier.stages),
        "orderedStages": sum(1 for stage in dossier.stages if stage.order is not None),
        "materials": len(dossier.materials),
        "tools": len(dossier.tools),
        "reactions": len(dossier.reactions),
        "environment": len(dossier.environment),
        "terms": len(dossier.glossary),
        "conflicts": len(dossier.conflicts),
        "openQuestions": len(dossier.open_questions),
        "pictures": len(dossier.pictures),
        "overviewSections": len(dossier.overview.sections),
    }


def _entry(result: DossierResult) -> IndexEntry:
    status = "FAIL" if result.problems else "PASS"
    check = IndexCheck(
        status=status,
        problems=len(result.problems),
        verified_at=result.check.checked_at if result.check is not None else None,
    )
    dossier = result.dossier
    if dossier is None:
        return IndexEntry(craft_slug=result.path.stem, file=result.path.name, check=check)
    disciplines = Counter(claim.discipline for claim in dossier.claims)
    reliabilities = Counter(source.reliability for source in dossier.sources)
    return IndexEntry(
        craft_slug=dossier.craft_slug,
        file=result.path.name,
        version=dossier.version,
        coverage=dossier.coverage,
        curated_at=dossier.curated_at,
        counts=part_counts(dossier),
        claims_by_discipline={name: disciplines[name] for name in DISCIPLINES if disciplines[name]},
        sources_by_reliability={tier: reliabilities[tier] for tier in RELIABILITIES},
        check=check,
    )


def _publisher(dossier: Dossier, source_id: str) -> str:
    source = dossier.source(source_id)
    return (source.publisher or urlsplit(source.url).hostname or source.url).casefold()
