import json
import uuid
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.research.terms import Term
from app.services.knowledge_view import ClaimView
from app.services.term_research import GlossaryTerm, ResearchedSummary, TermConceptRef
from app.services.term_summaries import StoredClaims

GOLDEN_TERM = Path(__file__).resolve().parents[3] / "shared" / "explainer.term.golden.json"
CHECKED_AT = datetime(2026, 11, 17, 10, 30, tzinfo=UTC)
KUT_ID = uuid.UUID("5a1d2c3e-0000-4000-8000-00000000c0de")
KUT_CONCEPT = uuid.UUID("5a1d2c3e-0000-4000-8000-00000000c0c0")


def golden_term() -> dict[str, Any]:
    return json.loads(GOLDEN_TERM.read_text(encoding="utf-8"))


def kut_term() -> GlossaryTerm:
    return GlossaryTerm(
        id=KUT_ID,
        key="kut",
        label="Kut",
        meaning="iron-water black paste",
        craft_slugs=("Kutch-Ajrakh",),
        craft_names=("Kutch Ajrakh",),
        concepts=(
            TermConceptRef(KUT_CONCEPT, "Kutch-Ajrakh", "MATERIAL", "Kut (iron-water black paste)", None),
        ),
    )


def golden_claims() -> StoredClaims:
    golden = golden_term()
    sentence = golden["summary"][0]
    view = ClaimView(
        id=uuid.UUID(sentence["citations"][0]["claimId"]),
        text=sentence["text"],
        level=sentence["level"],
        concept_type="MATERIAL",
        concept_id=KUT_CONCEPT,
        citations=sentence["citations"],
    )
    return StoredClaims(views=[view], sources={source["id"]: source for source in golden["sources"]})


@dataclass
class FakeTermStore:
    terms: dict[str, GlossaryTerm]
    stored: StoredClaims = field(default_factory=StoredClaims)
    written: StoredClaims = field(default_factory=StoredClaims)
    cache: dict[tuple[uuid.UUID, str], Term] = field(default_factory=dict)
    calls: Counter = field(default_factory=Counter)

    async def term(self, key: str) -> GlossaryTerm | None:
        self.calls["term"] += 1
        return self.terms.get(key)

    async def cached(self, term_id: uuid.UUID, language: str) -> Term | None:
        self.calls["cached"] += 1
        return self.cache.get((term_id, language))

    async def defining_claims(self, term: GlossaryTerm) -> StoredClaims:
        self.calls["defining_claims"] += 1
        return self.stored

    async def write_back(self, term: GlossaryTerm, researched: ResearchedSummary) -> list[uuid.UUID]:
        self.calls["write_back"] += 1
        return [view.id for view in self.written.views][: len(researched.sentences)]

    async def cited(self, claim_ids: Sequence[uuid.UUID]) -> StoredClaims:
        self.calls["cited"] += 1
        views = [view for view in self.written.views if view.id in set(claim_ids)]
        return StoredClaims(views=views, sources=self.written.sources)

    async def remember(self, term_id: uuid.UUID, summary: Term) -> None:
        self.calls["remember"] += 1
        self.cache[(term_id, summary.language)] = summary


@dataclass
class FakeResearch:
    found: ResearchedSummary | None
    calls: int = 0

    async def researched(self, term: GlossaryTerm) -> ResearchedSummary | None:
        self.calls += 1
        return self.found
