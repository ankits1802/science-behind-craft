from __future__ import annotations

import logging
import uuid
from collections.abc import Collection, Mapping, Sequence
from dataclasses import dataclass
from itertools import combinations

from pydantic import ValidationError

from app.composer.candidates import stored_claim_candidate
from app.composer.expert_takes import PanelAsk, PanelDraft, ProposedDifference, SeatTake, compose_takes
from app.research.blocks import ExplainerSentence
from app.research.blocks_people import ExpertDifference, ExpertViewBlock, expert_pairing_problems
from app.research.composition import ComposeCandidate, ComposeFocus
from app.research.expert_panel import EXPERT_PANEL, speaking_seats
from app.research.explainer import Block
from app.research.vocabulary import FACT_LEVELS

from .answer_events import CitedClaims
from .builder_interface import BuildAsk, BuilderTools, Built
from .knowledge_view import ClaimView
from .section_blocks import KeptSentence, cited_sentence, prose_problems

__all__ = [
    "EXPERT_VIEW_WAIT_SECONDS",
    "ExpertPanelBuilder",
    "difference_refusal",
    "expert_views",
    "panel_candidates",
]

logger = logging.getLogger(__name__)

EXPERT_VIEW_WAIT_SECONDS = 45.0

Take = tuple[KeptSentence, ...]


class ExpertPanelBuilder:
    def __init__(self, tools: BuilderTools) -> None:
        self._tools = tools

    async def build(self, ask: BuildAsk) -> Built:
        seats = speaking_seats(ask.section.discipline, ask.request.seats, depth=ask.request.depth)
        candidates = panel_candidates(ask.cited, ask.blocks)
        if not seats or not candidates or not ask.blocks:
            return Built()
        panel = PanelAsk(
            question=ask.request.question,
            craft=ask.request.craft,
            focus=ComposeFocus(discipline=ask.section.discipline, title=ask.section.title),
            seats=tuple(EXPERT_PANEL[seat] for seat in seats),
            candidates=tuple(candidates),
        )
        views = expert_views(ask.section.id, await compose_takes(self._tools.compose_model, panel), ask.cited)
        cited = dict.fromkeys(source_id for view in views for source_id in view.cited_source_ids())
        missing = [source_id for source_id in cited if source_id not in ask.cited.sources]
        if missing:
            logger.warning("the expert views of %s cite unknown sources %s", ask.section.id, missing)
            return Built()
        return Built(tuple(views), {source_id: ask.cited.sources[source_id] for source_id in cited})


@dataclass(frozen=True)
class _Panel:
    takes: Mapping[str, Take]
    differences: tuple[ProposedDifference, ...]
    agreeing: Mapping[str, tuple[str, ...]]
    cited: CitedClaims


def panel_candidates(cited: CitedClaims, blocks: Sequence[Block]) -> list[ComposeCandidate]:
    shown = dict.fromkeys(citation.claim_id for block in blocks for citation in block.citations())
    rest = sorted(str(claim_id) for claim_id in cited.views if str(claim_id) not in shown)
    views = [_stored(claim, cited) for claim in [*shown, *rest]]
    return [_candidate(view) for view in views if view is not None]


def expert_views(section_id: str, draft: PanelDraft, cited: CitedClaims) -> list[ExpertViewBlock]:
    takes = {take.seat: kept for take in draft.takes if (kept := _kept_take(take, cited)) is not None}
    differences = _kept_differences(draft.differences, takes, cited)
    panel = _Panel(takes, differences, _agreements(takes, differences), cited)
    try:
        views = [_view(f"{section_id}.{seat.lower().replace('_', '-')}", seat, panel) for seat in takes]
    except ValidationError as refused:
        logger.warning("the expert views of %s are refused: %s", section_id, refused)
        return []
    problems = expert_pairing_problems(views)
    if problems:
        logger.warning("the expert views of %s are refused: %s", section_id, "; ".join(problems))
        return []
    return views


def difference_refusal(
    proposal: ProposedDifference, seats: Collection[str], cited: CitedClaims
) -> str | None:
    if proposal.seat == proposal.other_seat:
        return "an expert does not differ with itself"
    if proposal.seat not in seats or proposal.other_seat not in seats:
        return "both experts give a view"
    mine, theirs = _stored(proposal.claim, cited), _stored(proposal.other_claim, cited)
    if mine is None or theirs is None:
        return "both statements are stored claims the section rests on"
    if mine.id == theirs.id:
        return "a statement does not differ with itself"
    shared = _source_ids(mine) & _source_ids(theirs)
    if shared:
        return f"both statements cite {', '.join(sorted(shared))}"
    if mine.concept_id is None or mine.concept_id != theirs.concept_id:
        return "the statements concern different subjects"
    return None


def _kept_take(take: SeatTake, cited: CitedClaims) -> Take | None:
    problems = [
        f"{s.raw_text!r}: {'; '.join(s.problems) or 'unreadable'}" for s in take.sentences if not s.passes
    ]
    if not take.sentences or problems:
        logger.warning("the %s view is dropped: %s", take.seat, " | ".join(problems) or "no sentence")
        return None
    kept = tuple(
        KeptSentence(s.sentence.text, tuple(s.sentence.claim_ids), tuple(s.sentence.evidence_ids), False)
        for s in take.sentences
        if s.sentence is not None
    )
    checked = prose_problems(kept, cited)
    if checked:
        logger.warning("the %s view is dropped: %s", take.seat, "; ".join(checked))
        return None
    return kept


def _kept_differences(
    proposals: Sequence[ProposedDifference], takes: Mapping[str, Take], cited: CitedClaims
) -> tuple[ProposedDifference, ...]:
    kept: list[ProposedDifference] = []
    paired: set[frozenset[str]] = set()
    for proposal in proposals:
        pair = frozenset({proposal.seat, proposal.other_seat})
        refusal = difference_refusal(proposal, takes, cited)
        if refusal is None and pair in paired:
            refusal = "the two experts already differ"
        if refusal is not None:
            logger.info("experts differ is refused for %s: %s", "+".join(sorted(pair)), refusal)
            continue
        paired.add(pair)
        kept.append(proposal)
    return tuple(kept)


def _agreements(
    takes: Mapping[str, Take], differences: Sequence[ProposedDifference]
) -> dict[str, tuple[str, ...]]:
    differing = {frozenset({d.seat, d.other_seat}) for d in differences}
    claims = {seat: {claim for s in take for claim in s.claim_ids} for seat, take in takes.items()}
    agreeing: dict[str, list[str]] = {seat: [] for seat in takes}
    for one, other in combinations(takes, 2):
        if frozenset({one, other}) not in differing and claims[one] & claims[other]:
            agreeing[one].append(other)
            agreeing[other].append(one)
    return {seat: tuple(seats) for seat, seats in agreeing.items()}


def _view(block_id: str, seat: str, panel: _Panel) -> ExpertViewBlock:
    take = [
        _sentence(f"{block_id}.{n}", sentence, panel.cited) for n, sentence in enumerate(panel.takes[seat], 1)
    ]
    differs: list[ExpertDifference] = []
    for other, mine, theirs in _sides(seat, panel.differences):
        number = len(take) + 2 * len(differs)
        differs.append(
            ExpertDifference(
                seat=other,
                this_view=_claim_sentence(f"{block_id}.{number + 1}", mine, panel.cited),
                other_view=_claim_sentence(f"{block_id}.{number + 2}", theirs, panel.cited),
            )
        )
    return ExpertViewBlock(
        id=block_id,
        kind="expert_view",
        version=1,
        reuse=None,
        seat=seat,
        take=take,
        agrees_with=list(panel.agreeing[seat]),
        differs=differs,
    )


def _sides(seat: str, differences: Sequence[ProposedDifference]) -> list[tuple[str, str, str]]:
    sides = []
    for difference in differences:
        if difference.seat == seat:
            sides.append((difference.other_seat, difference.claim, difference.other_claim))
        elif difference.other_seat == seat:
            sides.append((difference.seat, difference.other_claim, difference.claim))
    return sides


def _sentence(sentence_id: str, sentence: KeptSentence, cited: CitedClaims) -> ExplainerSentence:
    return ExplainerSentence.model_validate(cited_sentence(sentence_id, sentence, cited) | {"terms": []})


def _claim_sentence(sentence_id: str, claim: str, cited: CitedClaims) -> ExplainerSentence:
    view = cited.views[uuid.UUID(claim)]
    return _sentence(sentence_id, KeptSentence(view.text, (view.id,), (), False), cited)


def _stored(claim: str, cited: CitedClaims) -> ClaimView | None:
    try:
        view = cited.views.get(uuid.UUID(claim))
    except ValueError:
        return None
    return view if view is not None and view.level in FACT_LEVELS else None


def _candidate(view: ClaimView) -> ComposeCandidate:
    quotes = list(dict.fromkeys(c["quote"] for c in view.citations if c.get("quote")))
    return stored_claim_candidate(view.id, view.text, view.level).model_copy(update={"quotes": quotes})


def _source_ids(view: ClaimView) -> set[str]:
    return {str(citation["sourceId"]) for citation in view.citations}
