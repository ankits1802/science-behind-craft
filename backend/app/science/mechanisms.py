from __future__ import annotations

import uuid
from collections.abc import Iterable, Sequence
from dataclasses import dataclass

from app.research.blocks import ExplainerSentence
from app.research.blocks_play import SimulationReaction
from app.research.citations import Citation
from app.research.explainer import Block
from app.research.quotes import content_words
from app.research.vocabulary import FACT_LEVELS
from app.schemas.science import CitedClaim, ProcessStageView, ReactionView

from .process_view import craft_process
from .records import ProcessRecords

__all__ = [
    "CONCEPT_WORDS_MAX",
    "GENERIC_WORDS",
    "RESIST_ROLE",
    "Concept",
    "section_concepts",
    "simulation_reaction",
]

RESIST_ROLE = "RESIST"
CONCEPT_WORDS_MAX = 2
GENERIC_WORDS = frozenset(
    {
        "acid",
        "bath",
        "cloth",
        "color",
        "colour",
        "deep",
        "dye",
        "electron",
        "fast",
        "fibre",
        "fiber",
        "hydrogen",
        "mordant",
        "oxygen",
        "paste",
        "water",
    }
)


@dataclass(frozen=True)
class Concept:
    key: str
    label: str
    words: tuple[str, ...]
    reactions: tuple[ReactionView, ...]
    claims: tuple[CitedClaim, ...]
    shown_claim_ids: tuple[uuid.UUID, ...]
    position: int


@dataclass(frozen=True)
class _Candidate:
    key: str
    label: str
    surfaces: tuple[str, ...]
    reactions: tuple[ReactionView, ...]
    claims: tuple[CitedClaim, ...]


def section_concepts(records: ProcessRecords, blocks: Sequence[Block]) -> list[Concept]:
    stages = [stage for process in craft_process(records).processes for stage in process.stages]
    candidates = [*_reaction_candidates(stages), *_resist_candidates(stages)]
    sentences = [s for block in blocks for s in block.cited_sentences() if isinstance(s, ExplainerSentence)]
    found = [concept for c in candidates if (concept := _placed(c, sentences)) is not None]
    return sorted(found, key=lambda concept: (concept.position, concept.key))


def simulation_reaction(view: ReactionView) -> SimulationReaction:
    return SimulationReaction(
        reaction_id=view.id,
        label=view.label,
        species=list(view.species),
        equation=view.equation,
        balanced=view.balanced,
        citations=list(_citations(view.claims)),
    )


def _reaction_candidates(stages: Sequence[ProcessStageView]) -> list[_Candidate]:
    views = [r for stage in stages for r in stage.reactions if all(c.level in FACT_LEVELS for c in r.claims)]
    return [_reaction_candidate(group) for group in _grouped(views)]


def _reaction_candidate(group: Sequence[ReactionView]) -> _Candidate:
    surfaces = [s.name for view in group for s in view.species if s.name and not _generic(s.name)]
    return _Candidate(
        key=f"reaction:{group[0].id}",
        label="; ".join(view.label for view in group),
        surfaces=tuple(dict.fromkeys(surfaces)),
        reactions=tuple(group),
        claims=tuple(_unique_claims(claim for view in group for claim in view.claims)),
    )


def _resist_candidates(stages: Sequence[ProcessStageView]) -> list[_Candidate]:
    found: list[_Candidate] = []
    for stage in stages:
        resists = [m for m in stage.materials if m.role == RESIST_ROLE and m.level in FACT_LEVELS]
        if not resists:
            continue
        names = tuple(dict.fromkeys(material.name for material in resists))
        found.append(
            _Candidate(
                key=f"resist:{stage.id}",
                label=f"Resist in {stage.name}: {', '.join(names)}",
                surfaces=names,
                reactions=(),
                claims=tuple(_unique_claims(c for m in resists for c in m.claims if c.level in FACT_LEVELS)),
            )
        )
    return found


def _grouped(views: Sequence[ReactionView]) -> list[list[ReactionView]]:
    groups: list[tuple[set[str], list[int]]] = []
    for index, view in enumerate(views):
        marks = _marks(view)
        joined = [n for n, group in enumerate(groups) if group[0] & marks]
        merged_marks = marks.union(*(groups[n][0] for n in joined))
        merged = sorted([*(i for n in joined for i in groups[n][1]), index])
        groups = [group for n, group in enumerate(groups) if n not in joined] + [(merged_marks, merged)]
    ordered = sorted((members for _, members in groups), key=lambda members: members[0])
    return [[views[i] for i in members] for members in ordered]


def _marks(view: ReactionView) -> set[str]:
    marks = {f"compound:{s.compound_id}" for s in view.species if s.compound_id is not None}
    for species in view.species:
        marks |= {f"word:{word}" for word in _words(species.name or "")}
    return marks


def _placed(candidate: _Candidate, sentences: Sequence[ExplainerSentence]) -> Concept | None:
    claim_ids = {str(claim.id) for claim in candidate.claims}
    shown: list[uuid.UUID] = []
    position: int | None = None
    for index, sentence in enumerate(sentences):
        cited = [uuid.UUID(c.claim_id) for c in sentence.citations]
        if claim_ids & {str(c) for c in cited} or _names(sentence, candidate.surfaces):
            position = index if position is None else position
            shown += cited
    if position is None:
        return None
    return Concept(
        key=candidate.key,
        label=candidate.label,
        words=_search_words(candidate),
        reactions=candidate.reactions,
        claims=candidate.claims,
        shown_claim_ids=tuple(dict.fromkeys(shown)),
        position=position,
    )


def _names(sentence: ExplainerSentence, surfaces: Iterable[str]) -> bool:
    shown = {word for text in _sentence_texts(sentence) for word in _words(text)}
    return any(set(_words(surface)) <= shown and _words(surface) for surface in surfaces)


def _sentence_texts(sentence: ExplainerSentence) -> list[str]:
    return [sentence.original or sentence.text, *(c.quote for c in sentence.citations if c.quote)]


def _search_words(candidate: _Candidate) -> tuple[str, ...]:
    linked = [
        s.name for view in candidate.reactions for s in view.species if s.compound_id is not None and s.name
    ]
    return tuple(dict.fromkeys(linked or candidate.surfaces))[:CONCEPT_WORDS_MAX]


def _words(text: str) -> list[str]:
    return [
        word.removesuffix("s") for word in content_words(text) if word.removesuffix("s") not in GENERIC_WORDS
    ]


def _generic(name: str) -> bool:
    return not _words(name)


def _unique_claims(claims: Iterable[CitedClaim]) -> list[CitedClaim]:
    return list({claim.id: claim for claim in claims}.values())


def _citations(claims: Iterable[CitedClaim]) -> Iterable[Citation]:
    return dict.fromkeys(citation for claim in claims for citation in claim.citations)
