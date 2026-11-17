from __future__ import annotations

import uuid
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass

from app.research.craft_page import (
    DifferRow,
    PageArea,
    PageCommunity,
    PagePicture,
    PagePlace,
    PageProcess,
    PageQuestion,
    PageReaction,
    PageSpecies,
    PageStage,
    PageTerm,
    StageItem,
    StageTiming,
)
from app.research.reactions import ReactionSpecies, mhchem_equation
from app.science.records import ProcessRecords, ReactionRecord, StageRecord

from .craft_page_records import CraftPageRecords
from .curated_index import CuratedPage, IndexReaction, IndexStage, IndexTiming
from .curation_keys import TOOL_ROLE
from .curation_structure import species_label

__all__ = [
    "Visible",
    "page_communities",
    "page_differ",
    "page_glossary",
    "page_pictures",
    "page_places",
    "page_process",
    "page_questions",
]

DURATION = "DURATION"


@dataclass(frozen=True)
class Visible:
    levels: Mapping[uuid.UUID, str]
    order: Mapping[uuid.UUID, int]

    def keep(self, claim_ids: Iterable[uuid.UUID]) -> list[uuid.UUID]:
        return [claim_id for claim_id in dict.fromkeys(claim_ids) if claim_id in self.levels]

    def ranked(self, claim_ids: Iterable[uuid.UUID]) -> list[uuid.UUID]:
        return sorted(self.keep(claim_ids), key=lambda claim_id: self.order[claim_id])

    def all_shown(self, claim_ids: Sequence[uuid.UUID]) -> bool:
        return bool(claim_ids) and all(claim_id in self.levels for claim_id in claim_ids)


def page_differ(curated: CuratedPage | None, visible: Visible) -> list[DifferRow]:
    rows = [(item.about, visible.keep(item.claim_ids)) for item in curated.conflicts] if curated else []
    return [DifferRow(about=about, claim_ids=ids) for about, ids in rows if len(ids) >= 2]


def page_places(curated: CuratedPage | None, visible: Visible) -> list[PagePlace]:
    places = []
    for place in curated.places if curated else []:
        claims = visible.keep(place.claim_ids)
        if claims:
            places.append(
                PagePlace(
                    key=place.key,
                    name=place.name,
                    kind=place.kind,
                    role=place.role,
                    district=PageArea(lgd=place.district_lgd, name=place.district)
                    if place.district
                    else None,
                    state=PageArea(lgd=place.state_lgd, name=place.state) if place.state else None,
                    country=place.country,
                    wikidata_id=place.wikidata_id,
                    claim_ids=claims,
                )
            )
    return places


def page_communities(curated: CuratedPage | None, visible: Visible) -> list[PageCommunity]:
    if curated is None:
        return []
    names = {place.key: place.name for place in curated.places}
    found = [(group, visible.keep(group.claim_ids)) for group in curated.communities]
    return [
        PageCommunity(
            key=group.key,
            kind=group.kind,
            name=group.name,
            local_names=group.local_names,
            honours=group.honours,
            place=names.get(group.place_key) if group.place_key else None,
            claim_ids=claims,
        )
        for group, claims in found
        if claims
    ]


def page_questions(curated: CuratedPage | None, visible: Visible) -> list[PageQuestion]:
    found = [(item, visible.keep(item.claim_ids)) for item in curated.open_questions] if curated else []
    return [
        PageQuestion(key=item.key, question=item.question, settled_by=item.settled_by, claim_ids=claims)
        for item, claims in found
        if claims
    ]


def page_glossary(records: CraftPageRecords, visible: Visible) -> list[PageTerm]:
    if records.curated is None:
        return [
            PageTerm(
                key=term.key,
                label=term.label,
                names=list(term.names),
                meaning=None,
                language=None,
                script=None,
                claim_ids=[],
            )
            for term in records.terms
        ]
    return [
        PageTerm(
            key=term.term_key,
            label=term.names[0] if term.names else term.term,
            names=term.names,
            meaning=term.meaning,
            language=term.language,
            script=term.script,
            claim_ids=visible.keep(term.claim_ids),
        )
        for term in records.curated.glossary
    ]


def page_pictures(records: CraftPageRecords, visible: Visible) -> list[PagePicture]:
    curated = records.curated
    if curated is None:
        return [
            PagePicture(
                media=item.media,
                caption=item.media.title,
                stage_id=None,
                claim_ids=visible.keep(item.claim_ids),
            )
            for item in records.pictures
        ]
    stages = {stage.key: stage.stage_id for stage in curated.stages}
    shown = []
    for picture in curated.pictures:
        media = records.media.get(picture.media_ref_id)
        claims = visible.keep(picture.claim_ids)
        stage = stages.get(picture.stage_key) if picture.stage_key else None
        if media is not None and (claims or stage):
            shown.append(PagePicture(media=media, caption=picture.caption, stage_id=stage, claim_ids=claims))
    return shown


def page_process(records: CraftPageRecords, visible: Visible) -> PageProcess:
    curated = records.curated
    if curated is not None:
        return _curated_process(curated, records.process, visible)
    counts = {
        p.id: sum(1 for stage in records.process.stages if stage.process_id == p.id)
        for p in records.process.processes
    }
    chosen = max(records.process.processes, key=lambda p: (counts[p.id], p.name), default=None)
    if chosen is None:
        return PageProcess(process_id=None, stages=[], reactions=[])
    stages = sorted((s for s in records.process.stages if s.process_id == chosen.id), key=lambda s: s.ordinal)
    shown = [_stored_stage(stage, records.process, visible) for stage in stages]
    return PageProcess(process_id=chosen.id, stages=[stage for stage in shown if stage], reactions=[])


def _stored_stage(stage: StageRecord, records: ProcessRecords, visible: Visible) -> PageStage | None:
    claims = visible.ranked(stage.claim_ids)
    if not claims:
        return None
    materials, tools = _items(records, stage.id, visible, {})
    timing = [
        StageTiming(kind=DURATION, text=reading.stated, claim_id=reading.claim_id)
        for condition in records.conditions
        if condition.owner_id == stage.id and condition.quantity == DURATION
        for reading in condition.readings
        if reading.claim_id in visible.levels
    ]
    return PageStage(
        id=stage.id,
        order=stage.ordinal if stage.ordered and stage.ordinal >= 1 else None,
        name=stage.name,
        local_name=None,
        stage_type=stage.stage_type,
        claim_ids=claims,
        materials=materials,
        tools=tools,
        timing=timing,
        reactions=_reactions(records, stage.id, visible),
    )


def _curated_process(curated: CuratedPage, records: ProcessRecords, visible: Visible) -> PageProcess:
    rows = {stage.id: stage for stage in records.stages if stage.process_id == curated.process_id}
    names = {item.material_id: item.local_names for item in [*curated.materials, *curated.tools]}
    entries = sorted(
        (entry for entry in curated.stages if entry.stage_id in rows), key=lambda e: rows[e.stage_id].ordinal
    )
    shown = [_curated_stage(entry, rows[entry.stage_id], records, (visible, names)) for entry in entries]
    unstaged = [_index_reaction(item, visible) for item in curated.reactions if item.reaction_id is None]
    return PageProcess(
        process_id=curated.process_id,
        stages=[stage for stage in shown if stage],
        reactions=[reaction for reaction in unstaged if reaction],
    )


def _curated_stage(
    entry: IndexStage,
    stage: StageRecord,
    records: ProcessRecords,
    shown: tuple[Visible, Mapping[uuid.UUID, list[str]]],
) -> PageStage | None:
    visible, names = shown
    claims = visible.keep(entry.claim_ids)
    if not claims:
        return None
    materials, tools = _items(records, stage.id, visible, names)
    timing = [
        StageTiming(kind=kind, text=found.text, claim_id=found.claim_id)
        for kind, found in (("DURATION", entry.duration), ("SEASON", entry.season))
        if isinstance(found, IndexTiming) and found.claim_id in visible.levels
    ]
    return PageStage(
        id=stage.id,
        order=entry.order,
        name=stage.name,
        local_name=entry.local_name,
        stage_type=stage.stage_type,
        claim_ids=claims,
        materials=materials,
        tools=tools,
        timing=timing,
        reactions=_reactions(records, stage.id, visible),
    )


def _items(
    records: ProcessRecords, stage_id: uuid.UUID, visible: Visible, names: Mapping[uuid.UUID, list[str]]
) -> tuple[list[StageItem], list[StageItem]]:
    materials: list[StageItem] = []
    tools: list[StageItem] = []
    for material in sorted(records.materials, key=lambda m: (m.role, m.name.casefold(), str(m.id))):
        claims = visible.ranked(material.claim_ids)
        if material.stage_id != stage_id or material.material_id is None or not claims:
            continue
        item = StageItem(
            id=material.material_id,
            name=material.name,
            kind=material.kind,
            role=material.role,
            local_names=names.get(material.material_id, []),
            claim_ids=claims,
        )
        (tools if material.role == TOOL_ROLE else materials).append(item)
    return materials, tools


def _reactions(records: ProcessRecords, stage_id: uuid.UUID, visible: Visible) -> list[PageReaction]:
    chosen = sorted(
        (r for r in records.reactions if r.stage_id == stage_id), key=lambda r: (r.ordinal, r.label)
    )
    shown = [_reaction(reaction, visible) for reaction in chosen]
    return [reaction for reaction in shown if reaction]


def _reaction(reaction: ReactionRecord, visible: Visible) -> PageReaction | None:
    claims = visible.ranked(claim_id for claim_id, _citation in reaction.citations)
    if not claims:
        return None
    weights = (
        reaction.coefficients
        if reaction.balanced and reaction.coefficients
        else (None,) * len(reaction.species)
    )
    species = [
        PageSpecies(role=item.role, name=item.name, formula=item.formula, coefficient=weight)
        for item, weight in zip(reaction.species, weights, strict=True)
    ]
    equation = mhchem_equation(
        [
            ReactionSpecies(
                role=s.role, formula=s.formula, name=s.name, coefficient=s.coefficient, compound_id=None
            )
            for s in species
        ]
    )
    balanced = reaction.balanced and equation is not None
    return PageReaction(
        id=reaction.id,
        kind=reaction.kind,
        label=reaction.label,
        species=species,
        balanced=balanced,
        equation=equation if balanced else None,
        claim_ids=claims,
    )


def _index_reaction(item: IndexReaction, visible: Visible) -> PageReaction | None:
    claims = visible.keep(item.claim_ids)
    if not claims:
        return None
    species = [
        PageSpecies(role="REACTANT", name=s.name, formula=s.formula, coefficient=None) for s in item.reactants
    ]
    species += [
        PageSpecies(role="PRODUCT", name=s.name, formula=s.formula, coefficient=None) for s in item.products
    ]
    label = species_label(item.kind, [s.name for s in item.reactants], [s.name for s in item.products])
    return PageReaction(
        id=None, kind=item.kind, label=label, species=species, balanced=False, equation=None, claim_ids=claims
    )
