from __future__ import annotations

import uuid
from collections.abc import Iterable, Mapping
from dataclasses import dataclass

from pydantic import ValidationError

from app.research.composition import ComposedAnswer, ComposedSentence
from app.research.evidence import Quote, SourceDocument
from app.research.evidence_pack import EvidencePack, PackedEvidence
from app.research.quotes import quote_occurs, trivial_quote
from app.research.vocabulary import CONCEPT_TYPE_DISCIPLINES
from app.research.write_back import ClaimWriteBack, FoundBy, WriteBackCitation, WriteBackSubject

__all__ = [
    "INFERRED_REASON",
    "QUOTED_REASON",
    "WRITE_BACK_PREDICATE",
    "SkippedSentence",
    "WriteBackPlan",
    "composed_sentences",
    "write_back_plan",
]

WRITE_BACK_PREDICATE = "states"
QUOTED_REASON = "Live research: the sentence rests on verbatim passages that passed the quote check"
INFERRED_REASON = "Live research: model inference from the cited sources without a passing quote"
SKIP_NO_EVIDENCE = "cites stored claims only"
SKIP_INVALID = "breaks the write-back contract"
SKIP_FIELD_ONLY = "a field interview alone supports only the speaker's own practice"
SKIP_FIELD_BESIDE = "a field interview supports another discipline only beside an A or B source"
FIELD_ONLY_DISCIPLINES = frozenset({"PROCESS", "MATERIALS", "DESIGN", "ECONOMICS"})
FIELD_FOUND_BY = ("field_voices",)
BESIDE_FIELD_TRUST = frozenset({"A", "B"})


@dataclass(frozen=True)
class SkippedSentence:
    text: str
    reason: str


@dataclass(frozen=True)
class WriteBackPlan:
    claims: tuple[ClaimWriteBack, ...]
    skipped: tuple[SkippedSentence, ...]
    sentence_keys: tuple[str | None, ...] = ()


@dataclass(frozen=True)
class _Context:
    pack: EvidencePack
    found_by: FoundBy
    answer_id: uuid.UUID | None
    documents: Mapping[str, SourceDocument]
    packed: Mapping[str, PackedEvidence]
    field_ids: frozenset[str] = frozenset()


def write_back_plan(
    pack: EvidencePack,
    answer: ComposedAnswer,
    *,
    found_by: FoundBy,
    answer_id: uuid.UUID | None,
    field_documents: Mapping[str, SourceDocument] | None = None,
) -> WriteBackPlan:
    fields = dict(field_documents or {})
    context = _Context(
        pack=pack,
        found_by=found_by,
        answer_id=answer_id,
        documents={document.item.id: document for document in pack.documents} | fields,
        packed={entry.item.id: entry for entry in pack.evidence} | _field_packed(pack, fields),
        field_ids=frozenset(fields),
    )
    claims: list[ClaimWriteBack] = []
    skipped: list[SkippedSentence] = []
    keys: list[str | None] = []
    for sentence, heading in composed_sentences(answer):
        inferred = heading is None
        keys.append(None)
        cited = [ref for ref in sentence.evidence_ids if ref in context.documents and ref in context.packed]
        if not cited:
            skipped.append(SkippedSentence(sentence.text, SKIP_NO_EVIDENCE))
            continue
        refused = _field_refusal(context, cited)
        if refused is not None:
            skipped.append(SkippedSentence(sentence.text, refused))
            continue
        try:
            claim = _claim(sentence, cited, context, inferred=inferred)
        except ValidationError as error:
            skipped.append(SkippedSentence(sentence.text, f"{SKIP_INVALID}: {_first_error(error)}"))
            continue
        claims.append(claim)
        keys[-1] = claim.dedupe_key
    return WriteBackPlan(claims=_distinct(claims), skipped=tuple(skipped), sentence_keys=tuple(keys))


def composed_sentences(answer: ComposedAnswer) -> Iterable[tuple[ComposedSentence, str | None]]:
    for section in answer.sections:
        for sentence in section.sentences:
            yield sentence, section.heading
    for sentence in answer.open_questions:
        yield sentence, None


def _claim(
    sentence: ComposedSentence, cited: list[str], context: _Context, *, inferred: bool
) -> ClaimWriteBack:
    citations = [_citation(sentence, context.documents[ref], inferred=inferred) for ref in cited]
    quoted = not inferred and any(citation.quote_check == "PASS" for citation in citations)
    return ClaimWriteBack(
        craft_slug=context.pack.plan.craft.slug if context.pack.plan.craft else None,
        subject=_subject(context.pack, context.packed[_filing_ref(context, cited)]),
        predicate=WRITE_BACK_PREDICATE,
        text=sentence.text,
        label="QUOTED" if quoted else "INFERRED",
        level_reason=QUOTED_REASON if quoted else INFERRED_REASON,
        citations=citations,
        found_by=context.found_by,
        answer_id=context.answer_id,
    )


def _citation(sentence: ComposedSentence, document: SourceDocument, *, inferred: bool) -> WriteBackCitation:
    item = document.item
    quote = _passing_quote(sentence, document)
    if quote is None:
        return WriteBackCitation(evidence=item, quote=None, quote_check="NA", relation="CONTEXTUAL")
    known = [*item.quotes] if quote in item.quotes else [*item.quotes, quote]
    return WriteBackCitation(
        evidence=item.model_copy(update={"quotes": known}),
        quote=quote,
        quote_check="PASS",
        relation="CONTEXTUAL" if inferred else "DIRECT",
    )


def _passing_quote(sentence: ComposedSentence, document: SourceDocument) -> Quote | None:
    item = document.item
    for span in sentence.spans:
        if span.ref != item.id or trivial_quote(span.text) or not quote_occurs(span.text, document.text):
            continue
        same = next((quote for quote in item.quotes if quote.text == span.text), None)
        return same or Quote(text=span.text)
    return None


def _subject(pack: EvidencePack, entry: PackedEvidence) -> WriteBackSubject:
    facet = pack.plan.facets[entry.facet_indexes[0]]
    return WriteBackSubject(concept_type=facet.type, concept_name=facet.target)


def _field_packed(pack: EvidencePack, fields: Mapping[str, SourceDocument]) -> dict[str, PackedEvidence]:
    facets = _field_facets(pack) or (0,)
    return {
        key: PackedEvidence(
            item=document.item, facet_indexes=facets, found_by=FIELD_FOUND_BY, hits=1, best_rank=1
        )
        for key, document in fields.items()
    }


def _field_facets(pack: EvidencePack) -> tuple[int, ...]:
    return tuple(
        index
        for index, facet in enumerate(pack.plan.facets)
        if CONCEPT_TYPE_DISCIPLINES.get(facet.type) in FIELD_ONLY_DISCIPLINES
    )


def _filing_ref(context: _Context, cited: list[str]) -> str:
    return next((ref for ref in cited if ref not in context.field_ids), cited[0])


def _field_refusal(context: _Context, cited: list[str]) -> str | None:
    others = [ref for ref in cited if ref not in context.field_ids]
    if len(others) == len(cited):
        return None
    if not others:
        whole = len(_field_facets(context.pack)) == len(context.pack.plan.facets)
        return None if whole else SKIP_FIELD_ONLY
    facet = context.pack.plan.facets[context.packed[others[0]].facet_indexes[0]]
    if CONCEPT_TYPE_DISCIPLINES.get(facet.type) in FIELD_ONLY_DISCIPLINES:
        return None
    if any(context.documents[ref].item.trust in BESIDE_FIELD_TRUST for ref in others):
        return None
    return SKIP_FIELD_BESIDE


def _distinct(claims: list[ClaimWriteBack]) -> tuple[ClaimWriteBack, ...]:
    by_key: dict[str, ClaimWriteBack] = {}
    for claim in claims:
        kept = by_key.get(claim.dedupe_key)
        if kept is None:
            by_key[claim.dedupe_key] = claim
        elif kept.label == "INFERRED" and claim.label == "QUOTED":
            by_key[claim.dedupe_key] = claim.model_copy(
                update={"citations": [*claim.citations, *kept.citations]}
            )
        else:
            by_key[claim.dedupe_key] = kept.model_copy(
                update={"citations": [*kept.citations, *claim.citations]}
            )
    return tuple(by_key.values())


def _first_error(error: ValidationError) -> str:
    details = error.errors()
    return str(details[0]["msg"]) if details else str(error)
