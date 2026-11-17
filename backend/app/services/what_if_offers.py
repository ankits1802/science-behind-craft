from __future__ import annotations

import uuid
from collections.abc import Iterable, Iterator, Mapping, Sequence
from dataclasses import dataclass

from app.composer.what_if import WhatIfBrief, WhatIfInputBrief, WhatIfOptionBrief, WhatIfStatement
from app.research.alternatives import alternatives_named
from app.research.blocks import ExplainerSentence
from app.research.blocks_play import WHAT_IF_OPTIONS_MAX
from app.research.quotes import quote_occurs
from app.research.vocabulary import FACT_LEVELS
from app.science.records import KnownClaim, ProcessRecords, StageRecord

from .answer_events import CitedClaims
from .builder_evidence import known_claim, known_fact
from .builder_interface import BuildAsk
from .craft_matter import CraftMatter, MaterialRows, first_naming
from .what_if_evidence import CONTRAST_RELATION, OUTCOME_RELATIONS, WhatIfEvidence

__all__ = [
    "OUTCOMES_OFFERED_MAX",
    "WHAT_IF_INPUTS_MAX",
    "OfferedInput",
    "OfferedOption",
    "OfferedOutcome",
    "StageGroup",
    "group_concepts",
    "input_words",
    "named_groups",
    "what_if_brief",
    "what_if_inputs",
]

WHAT_IF_INPUTS_MAX = 4
OUTCOMES_OFFERED_MAX = 8


@dataclass(frozen=True)
class StageGroup:
    stage: StageRecord
    role: str
    materials: tuple[MaterialRows, ...]
    named: Mapping[uuid.UUID, int]


@dataclass(frozen=True)
class OfferedOutcome:
    ref: str
    claim: KnownClaim
    relation: str | None = None
    reaction_id: uuid.UUID | None = None

    @property
    def hypothesis(self) -> bool:
        return self.claim.level not in FACT_LEVELS


@dataclass(frozen=True)
class _Found:
    claim: KnownClaim
    relation: str | None = None
    reaction_id: uuid.UUID | None = None


@dataclass(frozen=True)
class OfferedOption:
    ref: str
    material: MaterialRows
    outcomes: tuple[OfferedOutcome, ...]


@dataclass(frozen=True)
class OfferedInput:
    ref: str
    stage: StageRecord
    role: str
    options: tuple[OfferedOption, ...]


def named_groups(matter: CraftMatter, sentences: Sequence[ExplainerSentence]) -> list[StageGroup]:
    stages = {stage.id: stage for stage in matter.records.stages}
    groups: list[StageGroup] = []
    for (stage_id, role), members in _role_members(matter.materials).items():
        named = {m.material_id: p for m in members if (p := _named_at(sentences, m)) is not None}
        if len(members) >= 2 and named and stage_id in stages:
            groups.append(StageGroup(stages[stage_id], role, members, named))
    return sorted(groups, key=lambda group: (min(group.named.values()), group.stage.ordinal, group.role))


def group_concepts(groups: Iterable[StageGroup]) -> list[uuid.UUID]:
    found = (_concept(material) for group in groups for material in group.materials)
    return list(dict.fromkeys(concept for concept in found if concept is not None))


def what_if_inputs(
    groups: Sequence[StageGroup], matter: CraftMatter, evidence: WhatIfEvidence, cited: CitedClaims
) -> list[OfferedInput]:
    ranked: list[tuple[int, StageGroup, tuple[MaterialRows, ...]]] = []
    for group in groups:
        for members in _alternatives(group, matter.records, evidence, cited):
            named = [group.named[m.material_id] for m in members if m.material_id in group.named]
            if named:
                ranked.append((min(named), group, members))
    ranked.sort(key=lambda entry: entry[0])
    return [
        _offered_input(f"i{n}", group, members, matter.records, evidence)
        for n, (_, group, members) in enumerate(ranked[:WHAT_IF_INPUTS_MAX], 1)
    ]


def what_if_brief(ask: BuildAsk, inputs: Sequence[OfferedInput]) -> WhatIfBrief:
    return WhatIfBrief(
        question=ask.request.english_question or ask.request.question,
        section=ask.section.title,
        inputs=tuple(_input_brief(offered) for offered in inputs),
    )


def input_words(offered: OfferedInput) -> list[str]:
    words = [offered.stage.name, offered.role]
    for option in offered.options:
        words += option.material.surfaces()
        words += [outcome.claim.text for outcome in option.outcomes]
    return words


def _role_members(materials: Iterable[MaterialRows]) -> dict[tuple[uuid.UUID, str], tuple[MaterialRows, ...]]:
    grouped: dict[tuple[uuid.UUID, str], dict[str, MaterialRows]] = {}
    for material in materials:
        for use in material.uses:
            members = grouped.setdefault((use.stage_id, use.role), {})
            members.setdefault(material.name.casefold(), material)
    return {slot: tuple(members.values()) for slot, members in grouped.items()}


def _named_at(sentences: Sequence[ExplainerSentence], material: MaterialRows) -> int | None:
    return first_naming(sentences, material.surfaces(), (term.key for term in material.terms))


def _concept(material: MaterialRows) -> uuid.UUID | None:
    return material.uses[0].concept_id


def _alternatives(
    group: StageGroup, records: ProcessRecords, evidence: WhatIfEvidence, cited: CitedClaims
) -> list[tuple[MaterialRows, ...]]:
    surfaces = {str(m.material_id): m.surfaces() for m in group.materials}
    joined = [
        frozenset(uuid.UUID(material) for material in together)
        for text in _relating_texts(group, records, evidence, cited)
        for together in alternatives_named(text, surfaces)
    ]
    joined += _contrasted(group, evidence)
    return _components(group.materials, joined)


def _contrasted(group: StageGroup, evidence: WhatIfEvidence) -> list[frozenset[uuid.UUID]]:
    by_concept = {_concept(m): m.material_id for m in group.materials if _concept(m) is not None}
    joined: list[frozenset[uuid.UUID]] = []
    for found in evidence.relationships:
        view = evidence.views.get(found.claim_id)
        if found.relation != CONTRAST_RELATION or view is None or known_fact(view) is None:
            continue
        joined.append(frozenset(by_concept[c] for c in found.concept_ids if c in by_concept))
    return joined


def _relating_texts(
    group: StageGroup, records: ProcessRecords, evidence: WhatIfEvidence, cited: CitedClaims
) -> Iterator[str]:
    yield group.stage.name
    claim_ids = list(group.stage.claim_ids)
    claim_ids += [
        claim for use in records.materials if use.stage_id == group.stage.id for claim in use.claim_ids
    ]
    found: list[KnownClaim | None] = [records.claims.get(claim) for claim in claim_ids]
    found += [known_fact(view) for view in (*evidence.views.values(), *cited.views.values())]
    facts = {fact.id: fact for fact in found if fact is not None and fact.level in FACT_LEVELS}
    for fact in facts.values():
        yield fact.text
        yield from (citation.quote for citation in fact.citations if citation.quote)


def _components(
    members: Sequence[MaterialRows], joined: Iterable[frozenset[uuid.UUID]]
) -> list[tuple[MaterialRows, ...]]:
    root = {member.material_id: member.material_id for member in members}

    def found(material: uuid.UUID) -> uuid.UUID:
        while root[material] != material:
            material = root[material]
        return material

    for together in joined:
        ids = sorted(material for material in together if material in root)
        for other in ids[1:]:
            root[found(other)] = found(ids[0])
    parts: dict[uuid.UUID, list[MaterialRows]] = {}
    for member in members:
        parts.setdefault(found(member.material_id), []).append(member)
    return [tuple(part) for part in parts.values() if len(part) >= 2]


def _offered_input(
    ref: str,
    group: StageGroup,
    members: Sequence[MaterialRows],
    records: ProcessRecords,
    evidence: WhatIfEvidence,
) -> OfferedInput:
    ordered = sorted(
        members,
        key=lambda m: (m.material_id not in group.named, group.named.get(m.material_id, 0), m.name),
    )
    options = tuple(
        OfferedOption(f"{ref}.o{n}", material, _offered_outcomes(f"{ref}.o{n}", material, records, evidence))
        for n, material in enumerate(ordered[:WHAT_IF_OPTIONS_MAX], 1)
    )
    return OfferedInput(ref, group.stage, group.role, options)


def _offered_outcomes(
    ref: str, material: MaterialRows, records: ProcessRecords, evidence: WhatIfEvidence
) -> tuple[OfferedOutcome, ...]:
    concept = _concept(material)
    found: list[_Found] = []
    if concept is not None:
        found += _related(concept, evidence)
        found += _own_facts(concept, evidence)
    found += _reacted(material, records)
    unique: dict[uuid.UUID, _Found] = {}
    for entry in found:
        unique.setdefault(entry.claim.id, entry)
    kept = list(unique.values())[:OUTCOMES_OFFERED_MAX]
    return tuple(
        OfferedOutcome(f"{ref}.e{n}", entry.claim, entry.relation, entry.reaction_id)
        for n, entry in enumerate(kept, 1)
    )


def _related(concept: uuid.UUID, evidence: WhatIfEvidence) -> list[_Found]:
    found: list[tuple[int, _Found]] = []
    for relationship in evidence.relationships_of(concept):
        view = evidence.views.get(relationship.claim_id)
        claim = known_claim(view) if view is not None else None
        if claim is not None:
            rank = OUTCOME_RELATIONS.index(relationship.relation)
            found.append((rank, _Found(claim, relationship.relation)))
    found.sort(key=lambda entry: (entry[0], entry[1].claim.level not in FACT_LEVELS))
    return [entry for _, entry in found]


def _own_facts(concept: uuid.UUID, evidence: WhatIfEvidence) -> list[_Found]:
    views = (evidence.views.get(claim) for claim in evidence.concept_claims.get(concept, ()))
    facts = (known_fact(view) for view in views if view is not None)
    return [_Found(fact) for fact in facts if fact is not None]


def _reacted(material: MaterialRows, records: ProcessRecords) -> list[_Found]:
    compound = material.compound
    if compound is None:
        return []
    names = (compound.name, *material.surfaces())
    found: list[_Found] = []
    for reaction in records.reactions:
        if compound.id not in {species.compound_id for species in reaction.species}:
            continue
        for claim_id, citation_id in reaction.citations:
            claim = records.claims.get(claim_id)
            if claim is not None and _linked_and_naming(claim, citation_id, names):
                found.append(_Found(claim, reaction_id=reaction.id))
    return found


def _linked_and_naming(claim: KnownClaim, citation_id: str, names: Sequence[str]) -> bool:
    if not any(citation.id == citation_id for citation in claim.citations):
        return False
    texts = [claim.text, *(citation.quote for citation in claim.citations if citation.quote)]
    return any(quote_occurs(name.casefold(), text.casefold()) for name in names for text in texts)


def _input_brief(offered: OfferedInput) -> WhatIfInputBrief:
    return WhatIfInputBrief(
        ref=offered.ref,
        stage=offered.stage.name,
        role=offered.role,
        options=tuple(
            WhatIfOptionBrief(option.ref, option.material.name, tuple(_statement(o) for o in option.outcomes))
            for option in offered.options
        ),
    )


def _statement(outcome: OfferedOutcome) -> WhatIfStatement:
    return WhatIfStatement(
        ref=outcome.ref,
        text=outcome.claim.text,
        hypothesis=outcome.hypothesis,
        relation=outcome.relation,
        reaction=outcome.reaction_id is not None,
    )
