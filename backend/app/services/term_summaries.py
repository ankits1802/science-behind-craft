from __future__ import annotations

import uuid
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Protocol

from app.core.errors import Refused
from app.research.citations import AnswerSentence, cited_source_ids
from app.research.terms import TERM_SCHEMA_VERSION, TERM_SUMMARY_MAX_SENTENCES, Term
from app.research.vocabulary import CANONICAL_LANGUAGE, FACT_LEVELS

from .answer_translation import AnswerTranslation, translated_sentences
from .knowledge_view import ClaimView
from .term_research import GlossaryTerm, ResearchedSummary

__all__ = [
    "NO_SUMMARY_REASON",
    "UNKNOWN_TERM_REASON",
    "StoredClaims",
    "TermLookup",
    "TermResearch",
    "TermStore",
    "term_view",
]

UNKNOWN_TERM_REASON = "unknown_term"
NO_SUMMARY_REASON = "no_cited_summary"
UNKNOWN_TERM_MESSAGE = "No term has that address."
NO_SUMMARY_MESSAGE = "This term has no cited summary yet."
STORED_BASIS = "STORED"


@dataclass(frozen=True)
class StoredClaims:
    views: Sequence[ClaimView] = ()
    sources: Mapping[str, dict[str, Any]] = field(default_factory=dict)


class TermStore(Protocol):
    async def term(self, key: str) -> GlossaryTerm | None: ...

    async def cached(self, term_id: uuid.UUID, language: str) -> Term | None: ...

    async def defining_claims(self, term: GlossaryTerm) -> StoredClaims: ...

    async def write_back(self, term: GlossaryTerm, researched: ResearchedSummary) -> list[uuid.UUID]: ...

    async def cited(self, claim_ids: Sequence[uuid.UUID]) -> StoredClaims: ...

    async def remember(self, term_id: uuid.UUID, summary: Term) -> None: ...


class TermResearch(Protocol):
    async def researched(self, term: GlossaryTerm) -> ResearchedSummary | None: ...


def utc_now() -> datetime:
    return datetime.now(UTC)


@dataclass(frozen=True)
class TermLookup:
    store: TermStore
    research: TermResearch
    translation: AnswerTranslation
    clock: Callable[[], datetime] = utc_now

    async def summary(self, key: str, language: str) -> Term:
        term = await self.store.term(key)
        if term is None:
            raise Refused(UNKNOWN_TERM_REASON, UNKNOWN_TERM_MESSAGE)
        found = await self.store.cached(term.id, language)
        if found is not None:
            return found
        english = None
        if language != CANONICAL_LANGUAGE:
            english = await self.store.cached(term.id, CANONICAL_LANGUAGE)
        if english is None:
            english = await self._english(term)
            await self.store.remember(term.id, english)
        if language == CANONICAL_LANGUAGE:
            return english
        translated = await self._translated(english, language)
        await self.store.remember(term.id, translated)
        return translated

    async def _english(self, term: GlossaryTerm) -> Term:
        stored = await self.store.defining_claims(term)
        if stored.views:
            return term_view(term, STORED_BASIS, stored, language=CANONICAL_LANGUAGE, checked_at=self.clock())
        researched = await self.research.researched(term)
        if researched is None:
            raise Refused(NO_SUMMARY_REASON, NO_SUMMARY_MESSAGE)
        claim_ids = list(dict.fromkeys(await self.store.write_back(term, researched)))
        cited = await self.store.cited(claim_ids)
        if not cited.views:
            raise Refused(NO_SUMMARY_REASON, NO_SUMMARY_MESSAGE)
        return term_view(term, researched.basis, cited, language=CANONICAL_LANGUAGE, checked_at=self.clock())

    async def _translated(self, english: Term, language: str) -> Term:
        sentences = [sentence.model_dump(mode="json", by_alias=True) for sentence in english.summary]
        translated = await translated_sentences(
            sentences, language=language, translation=self.translation, claim_texts=_claim_texts(english)
        )
        shown = english.model_dump(mode="json", by_alias=True)
        return Term.model_validate({**shown, "language": language, "summary": translated})


def term_view(
    term: GlossaryTerm, basis: str, claims: StoredClaims, *, language: str, checked_at: datetime
) -> Term:
    facts = [view for view in claims.views if view.level in FACT_LEVELS and view.citations]
    unique = list({view.id: view for view in facts}.values())[:TERM_SUMMARY_MAX_SENTENCES]
    if not unique:
        raise Refused(NO_SUMMARY_REASON, NO_SUMMARY_MESSAGE)
    summary = [
        AnswerSentence(id=f"{term.key}.{n}", text=view.text, level=view.level, citations=view.citations)
        for n, view in enumerate(unique, start=1)
    ]
    return Term(
        schema_version=TERM_SCHEMA_VERSION,
        key=term.key,
        label=term.label,
        language=language,
        local_names=list(term.local_names),
        craft_slugs=list(term.craft_slugs),
        wikidata_id=term.wikidata_id,
        basis=basis,
        summary=summary,
        sources=[claims.sources[source_id] for source_id in cited_source_ids(summary)],
        checked_at=checked_at,
    )


def _claim_texts(summary: Term) -> dict[uuid.UUID, str]:
    texts: dict[uuid.UUID, str] = {}
    for sentence in summary.summary:
        claims = {citation.claim_id for citation in sentence.citations}
        if len(claims) == 1:
            texts[uuid.UUID(claims.pop())] = sentence.original or sentence.text
    return texts
