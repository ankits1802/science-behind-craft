from __future__ import annotations

import hashlib
import uuid
from collections.abc import Iterable, Iterator, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime

from pydantic import Field, ValidationError

from .base import ContractModel
from .blocks_play import SIMULATION_VALUES_MAX, SimulationBlock, SimulationValue
from .citations import Citation
from .quotes import normalise_quote_text, numbers_in, quote_occurs
from .sandbox import SANDBOX_MAX_BYTES, SandboxProblem, sandbox_problems

__all__ = [
    "DRAFT_RULES",
    "OFFER_REF_PREFIX",
    "SIMULATION_HTML_MAX_CHARS",
    "STATED_MAX_CHARS",
    "STATED_WORDS_AROUND",
    "DraftCheck",
    "DraftValue",
    "OfferedValue",
    "SimulationDraft",
    "checked_draft",
    "data_object",
    "offered_values",
    "stated_figures",
]

DRAFT_RULES = ("VALUE", "BLOCK")
OFFER_REF_PREFIX = "v"
STATED_WORDS_AROUND = 3
STATED_MAX_CHARS = 200
CLAUSE_ENDS = (".", ",", ";", ":", "!", "?")
CLOSING_MARKS = "\"')]}"
STATED_EDGES = "\"'()[]{},;:.!? "
DRAFT_TEXT_MAX_CHARS = 200
SIMULATION_HTML_MAX_CHARS = 12000


@dataclass(frozen=True)
class OfferedValue:
    ref: str
    figure: str
    value: float
    stated: str
    citation: Citation

    @property
    def claim_id(self) -> uuid.UUID:
        return uuid.UUID(self.citation.claim_id)


class DraftValue(ContractModel):
    ref: str = Field(min_length=1, max_length=DRAFT_TEXT_MAX_CHARS)
    key: str = Field(min_length=1, max_length=DRAFT_TEXT_MAX_CHARS)
    label: str = Field(min_length=1, max_length=DRAFT_TEXT_MAX_CHARS)
    unit: str = Field(max_length=DRAFT_TEXT_MAX_CHARS)


class SimulationDraft(ContractModel):
    build: bool
    concept: str = Field(max_length=DRAFT_TEXT_MAX_CHARS)
    title: str = Field(max_length=DRAFT_TEXT_MAX_CHARS)
    values: list[DraftValue] = Field(max_length=SIMULATION_VALUES_MAX)
    html: str = Field(max_length=SANDBOX_MAX_BYTES)


@dataclass(frozen=True)
class DraftCheck:
    block: SimulationBlock | None
    problems: tuple[SandboxProblem, ...]

    @property
    def rules(self) -> tuple[str, ...]:
        return tuple(sorted({problem.rule for problem in self.problems}))


def offered_values(citations: Iterable[Citation]) -> list[OfferedValue]:
    offered: dict[tuple[str, float], OfferedValue] = {}
    for citation in citations:
        for figure, value, stated in stated_figures(citation.quote or ""):
            seen = (citation.claim_id, value)
            if seen in offered:
                continue
            if len(offered) == SIMULATION_VALUES_MAX:
                return list(offered.values())
            ref = f"{OFFER_REF_PREFIX}{len(offered) + 1}"
            offered[seen] = OfferedValue(ref, figure, value, stated, citation)
    return list(offered.values())


def stated_figures(quote: str) -> Iterator[tuple[str, float, str]]:
    words = normalise_quote_text(quote).split(" ")
    for index, word in enumerate(words):
        for figure in numbers_in(word):
            value = _plain_number(figure)
            stated = _words_around(words, index)
            if value is not None and len(stated) <= STATED_MAX_CHARS and quote_occurs(stated, quote):
                yield figure, value, stated


def data_object(values: Sequence[SimulationValue]) -> dict[str, float]:
    return {value.key: value.value for value in values}


def checked_draft(
    draft: SimulationDraft,
    offers: Sequence[OfferedValue],
    *,
    block_id: str,
    model: str,
    created_at: datetime,
) -> DraftCheck:
    if len(draft.html) > SIMULATION_HTML_MAX_CHARS:
        detail = f"{len(draft.html)} characters, more than {SIMULATION_HTML_MAX_CHARS}"
        return DraftCheck(None, (SandboxProblem("SIZE", detail),))
    values, problems = _draft_values(draft, offers)
    if problems:
        return DraftCheck(None, tuple(problems))
    sandboxed = sandbox_problems(draft.html, data_object(values))
    if sandboxed:
        return DraftCheck(None, tuple(sandboxed))
    try:
        block = SimulationBlock(
            id=block_id,
            kind="simulation",
            version=1,
            reuse=None,
            concept=draft.concept,
            title=draft.title,
            model=model,
            created_at=created_at,
            html=draft.html,
            html_sha256=hashlib.sha256(draft.html.encode("utf-8")).hexdigest(),
            values=values,
            datasets=[],
            hidden=False,
        )
    except ValidationError as refused:
        return DraftCheck(None, tuple(SandboxProblem("BLOCK", message) for message in _messages(refused)))
    return DraftCheck(block, ())


def _draft_values(
    draft: SimulationDraft, offers: Sequence[OfferedValue]
) -> tuple[list[SimulationValue], list[SandboxProblem]]:
    by_ref: Mapping[str, OfferedValue] = {offer.ref: offer for offer in offers}
    refs = [chosen.ref for chosen in draft.values]
    problems = [
        SandboxProblem("VALUE", f"{ref} is used twice") for ref in sorted(set(refs)) if refs.count(ref) > 1
    ]
    if not refs:
        problems.append(SandboxProblem("VALUE", "no offered value is used"))
    values: list[SimulationValue] = []
    for chosen in draft.values:
        offer = by_ref.get(chosen.ref)
        if offer is None:
            problems.append(SandboxProblem("VALUE", f"{chosen.ref} is not an offered value"))
            continue
        try:
            values.append(_value(chosen, offer))
        except ValueError as refused:
            problems += [SandboxProblem("VALUE", message) for message in _messages(refused)]
    return values, problems


def _value(chosen: DraftValue, offer: OfferedValue) -> SimulationValue:
    unit = chosen.unit or None
    if unit is not None and not quote_occurs(unit, offer.stated):
        raise ValueError(f"value {chosen.key} gives the unit {unit!r}, which {offer.stated!r} does not")
    return SimulationValue(
        key=chosen.key,
        label=chosen.label,
        value=offer.value,
        unit=unit,
        stated=offer.stated,
        citations=[offer.citation],
        dataset_code=None,
    )


def _messages(refused: ValueError) -> list[str]:
    if isinstance(refused, ValidationError):
        return [str(error["msg"]) for error in refused.errors()]
    return [str(refused)]


def _words_around(words: Sequence[str], index: int) -> str:
    start = index
    while start > 0 and index - start < STATED_WORDS_AROUND and not _ends_clause(words[start - 1]):
        start -= 1
    end = index
    while end < len(words) - 1 and end - index < STATED_WORDS_AROUND and not _ends_clause(words[end]):
        end += 1
    return " ".join(words[start : end + 1]).strip(STATED_EDGES)


def _plain_number(figure: str) -> float | None:
    try:
        return float(figure)
    except ValueError:
        return None


def _ends_clause(word: str) -> bool:
    return word.rstrip(CLOSING_MARKS).endswith(CLAUSE_ENDS)
