from __future__ import annotations

import uuid
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from types import MappingProxyType

from sqlalchemy.ext.asyncio import AsyncSession

from app.curation.limits import SECTION_SENTENCES_MIN
from app.research.article_sections import SectionSentence
from app.research.candidate_gates import Candidate, HeldFact, statement_key
from app.research.candidate_judge import JudgeAsk, novelty_request, parsed_new_details
from app.research.section_proposals import (
    FAITHFUL,
    FIELD,
    HELD,
    SENTENCES,
    STATED,
    SectionCheck,
    SectionPart,
    first_refusal,
)
from app.research.structured import StructuredModel

from . import knowledge_view
from .answer_events import CitedClaims
from .candidate_gates import asked_judges
from .claim_holds import unheld_by_id
from .coverage import coverage_of
from .knowledge_api import claim_fields
from .knowledge_view import ClaimView
from .open_work_subjects import WorkSubject
from .page_held_facts import held_claims
from .section_blocks import KeptSentence, prose_problems

__all__ = [
    "ShownFacts",
    "faithful_check",
    "field_facts",
    "section_checks",
    "shown_facts",
    "stale_problem",
]

HELD_SIMILARITY = 1.0
SENTENCE_REF = "sentence-{number}"
NOT_HELD = "sentence {number} cites {ids}, which this page does not hold as a shown fact"
OTHER_FIELD = "sentence {number} cites {claim}, a fact of {fields}, not of {field}"
TOO_FEW = "the section holds {count} sentences, and the {facts} facts this page holds in {field} need at least {needed}"
UNFAITHFUL = "sentence {number} says what its facts do not: {details}"
PASSED: Mapping[str, str] = MappingProxyType(
    {
        HELD: "every fact the section cites is a shown fact of this page",
        FIELD: "every fact the section cites is a fact of its field",
        STATED: "every number, name, date and place the section states is in the facts it cites",
        FAITHFUL: "the judge ({model}) found nothing a sentence says that its facts do not",
    }
)
ENOUGH = "{count} sentences"
AS_MANY = "{count} sentences, as many as the {facts} facts this page holds in {field} allow"
RESTATED = "every sentence restates the fact it cites, so no judge was asked"
NO_FIELD = "no field"


@dataclass(frozen=True)
class ShownFacts:
    views: Mapping[uuid.UUID, ClaimView] = field(default_factory=dict)
    fields: Mapping[uuid.UUID, tuple[str, ...]] = field(default_factory=dict)
    in_field: int = 0


async def shown_facts(session: AsyncSession, subject: WorkSubject, part: SectionPart) -> ShownFacts:
    cited = part.claim_ids()
    held = await held_claims(session, subject, cited)
    visible, _ = await knowledge_view.claims_by_id(session, [claim for claim in cited if claim in held])
    shown = await unheld_by_id(session, visible)
    fields = await claim_fields(session, list(shown))
    return ShownFacts(views=shown, fields={claim: tuple(found) for claim, found in fields.items()})


async def field_facts(session: AsyncSession, subject: WorkSubject, part: SectionPart) -> ShownFacts:
    found = await shown_facts(session, subject, part)
    coverage = await coverage_of(session, subject)
    counted = next((entry.claims for entry in coverage.fields if entry.field == part.field), 0)
    cited = sum(1 for claim in found.views if part.field in found.fields.get(claim, ()))
    return ShownFacts(views=found.views, fields=found.fields, in_field=max(counted, cited))


def section_checks(part: SectionPart, facts: ShownFacts) -> list[SectionCheck]:
    return _in_order(part, facts, (_held, _field, _sentences, _stated))


def stale_problem(part: SectionPart, facts: ShownFacts) -> str | None:
    refused = first_refusal(_in_order(part, facts, (_held, _field, _stated)))
    return None if refused is None else "; ".join(refused.reasons)


async def faithful_check(
    part: SectionPart, facts: ShownFacts, judges: Sequence[StructuredModel]
) -> SectionCheck:
    asks = [
        JudgeAsk(_candidate(part, number, sentence), _held_facts(sentence, facts))
        for number, sentence in enumerate(part.sentences, start=1)
        if not _restates(sentence, facts)
    ]
    if not asks:
        return SectionCheck(check=FAITHFUL, passed=True, reasons=[RESTATED])
    found, model = await asked_judges(
        judges, novelty_request(asks), lambda reply: parsed_new_details(reply, asks)
    )
    reasons = [
        UNFAITHFUL.format(number=number, details="; ".join(details))
        for number, _ in enumerate(part.sentences, start=1)
        if (details := found.get(SENTENCE_REF.format(number=number)))
    ]
    passed = PASSED[FAITHFUL].format(model=model or "the judge")
    return SectionCheck(check=FAITHFUL, passed=not reasons, reasons=reasons or [passed])


Check = Callable[[SectionPart, ShownFacts], SectionCheck]


def _in_order(part: SectionPart, facts: ShownFacts, checks: Sequence[Check]) -> list[SectionCheck]:
    done: list[SectionCheck] = []
    for check in checks:
        done.append(check(part, facts))
        if not done[-1].passed:
            break
    return done


def _held(part: SectionPart, facts: ShownFacts) -> SectionCheck:
    reasons = [
        NOT_HELD.format(number=number, ids=", ".join(missing))
        for number, sentence in enumerate(part.sentences, start=1)
        if (missing := [str(claim) for claim in sentence.claim_ids if claim not in facts.views])
    ]
    return _checked(HELD, reasons, PASSED[HELD])


def _field(part: SectionPart, facts: ShownFacts) -> SectionCheck:
    reasons = [
        OTHER_FIELD.format(
            number=number, claim=claim, fields=_named(facts.fields.get(claim, ())), field=part.field
        )
        for number, sentence in enumerate(part.sentences, start=1)
        for claim in sentence.claim_ids
        if part.field not in facts.fields.get(claim, ())
    ]
    return _checked(FIELD, reasons, PASSED[FIELD])


def _sentences(part: SectionPart, facts: ShownFacts) -> SectionCheck:
    count, held = len(part.sentences), facts.in_field
    needed = min(SECTION_SENTENCES_MIN, held)
    if count < needed:
        reason = TOO_FEW.format(count=count, facts=held, field=part.field, needed=needed)
        return SectionCheck(check=SENTENCES, passed=False, reasons=[reason])
    said = ENOUGH if count >= SECTION_SENTENCES_MIN else AS_MANY
    return SectionCheck(
        check=SENTENCES, passed=True, reasons=[said.format(count=count, facts=held, field=part.field)]
    )


def _stated(part: SectionPart, facts: ShownFacts) -> SectionCheck:
    kept = [KeptSentence(s.text, tuple(s.claim_ids), (), False) for s in part.sentences]
    return _checked(STATED, prose_problems(kept, CitedClaims(views=facts.views)), PASSED[STATED])


def _checked(check: str, reasons: list[str], passed: str) -> SectionCheck:
    return SectionCheck(check=check, passed=not reasons, reasons=reasons or [passed])


def _named(fields: Sequence[str]) -> str:
    return " and ".join(fields) if fields else NO_FIELD


def _candidate(part: SectionPart, number: int, sentence: SectionSentence) -> Candidate:
    return Candidate(ref=SENTENCE_REF.format(number=number), statement=sentence.text, field=part.field)


def _held_facts(sentence: SectionSentence, facts: ShownFacts) -> tuple[HeldFact, ...]:
    return tuple(
        HeldFact(id=claim, text=facts.views[claim].text, similarity=HELD_SIMILARITY)
        for claim in sentence.claim_ids
    )


def _restates(sentence: SectionSentence, facts: ShownFacts) -> bool:
    said = statement_key(sentence.text)
    return any(statement_key(facts.views[claim].text) == said for claim in sentence.claim_ids)
