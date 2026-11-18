from __future__ import annotations

import uuid
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field

from app.research.craft_page import (
    DifferRow,
    PageArea,
    PageCommunity,
    PagePicture,
    PagePlace,
    PageQuestion,
    PageTerm,
)
from app.research.craft_page_process import (
    PageProcess,
    PageReaction,
    PageSpecies,
    PageStage,
    StageItem,
    StageTiming,
)
from app.research.reactions import ReactionSpecies, mhchem_equation
from app.science.records import ProcessRecords, ReactionRecord, StageRecord

from .craft_page_family import ShownPicture, hero_index, shown_pictures
from .craft_page_records import CraftPageRecords
from .curated_index import CuratedPage, IndexReaction, IndexStage, IndexTiming
from .curation_keys import TOOL_ROLE
from .curation_structure import species_label

__all__ = [
    "ItemNames",
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
CENTRAL_DISCIPLINES = frozenset({"CHEMISTRY", "PHYSICS"})
SCIENCE_DISCIPLINES = frozenset({"PROCESS", "MATERIALS", "GEOLOGY", "CLIMATE", "ECOLOGY", "BOTANY", "HEALTH"})
CENTRAL_WEIGHT, SCIENCE_WEIGHT, OTHER_WEIGHT = 3, 2, 1
DIFFER_KEY = "differ-{number}"

ItemNames = tuple[list[str], str | None, int | None]


@dataclass(frozen=True)
class Visible:
    levels: Mapping[uuid.UUID, str]
    order: Mapping[uuid.UUID, int]
    disciplines: Mapping[uuid.UUID, str] = field(default_factory=dict)

    def keep(self, claim_ids: Iterable[uuid.UUID]) -> list[uuid.UUID]:
        return [claim_id for claim_id in dict.fromkeys(claim_ids) if claim_id in self.levels]

    def ranked(self, claim_ids: Iterable[uuid.UUID]) -> list[uuid.UUID]:
        return sorted(self.keep(claim_ids), key=lambda claim_id: self.order[claim_id])

    def all_shown(self, claim_ids: Sequence[uuid.UUID]) -> bool:
        return bool(claim_ids) and all(claim_id in self.levels for claim_id in claim_ids)


def page_differ(curated: CuratedPage | None, visible: Visible) -> list[DifferRow]:
    if curated is None:
        return []
    staged = {
        claim_id
        for stage in curated.stages
        for claim_id in [*stage.claim_ids, *(t.claim_id for t in (stage.duration, stage.season) if t)]
    }
    rows = []
    for number, item in enumerate(curated.conflicts, start=1):
        ids = visible.keep(item.claim_ids)
        if len(ids) >= 2:
            weight = _differ_weight(ids, staged, visible)
            key = DIFFER_KEY.format(number=number)
            rows.append(DifferRow(key=key, about=item.about, weight=weight, claim_ids=ids))
    return sorted(rows, key=lambda row: -row.weight)


def _differ_weight(claim_ids: Sequence[uuid.UUID], staged: set[uuid.UUID], visible: Visible) -> int:
    disciplines = {visible.disciplines.get(claim_id) for claim_id in claim_ids}
    if staged.intersection(claim_ids) or disciplines & CENTRAL_DISCIPLINES:
        return CENTRAL_WEIGHT
    return SCIENCE_WEIGHT if disciplines & SCIENCE_DISCIPLINES else OTHER_WEIGHT


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


def page_communities(
    curated: CuratedPage | None, visible: Visible, places: Sequence[PagePlace]
) -> list[PageCommunity]:
    if curated is None:
        return []
    names = {place.key: place.name for place in places}
    found = [(group, visible.keep(group.claim_ids)) for group in curated.communities]
    return [
        PageCommunity(
            key=group.key,
            kind=group.kind,
            name=group.name,
            local_names=group.local_names,
            honours=group.honours,
            place=names.get(group.place_key) if group.place_key else None,
            place_key=group.place_key if group.place_key in names else None,
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
    if records.curated is not None:
        return _with_roles(shown_pictures(records.curated, records.media, visible.levels))
    found = [
        ShownPicture(item.media, item.media.title, None, visible.keep(item.claim_ids))
        for item in records.pictures
    ]
    return _with_roles(found)


def _with_roles(found: Sequence[ShownPicture]) -> list[PagePicture]:
    hero = hero_index([(picture.media, picture.stage_id) for picture in found])
    return [
        PagePicture(
            media=picture.media,
            caption=picture.caption,
            role="HERO" if index == hero else "STAGE" if picture.stage_id else "OVERVIEW",
            stage_id=picture.stage_id,
            claim_ids=picture.claim_ids,
        )
        for index, picture in enumerate(found)
    ]


def page_process(records: CraftPageRecords, visible: Visible, differ: Sequence[DifferRow]) -> PageProcess:
    curated = records.curated
    if curated is not None:
        return _curated_process(curated, records.process, (visible, differ))
    counts = {
        p.id: sum(1 for stage in records.process.stages if stage.process_id == p.id)
        for p in records.process.processes
    }
    chosen = max(records.process.processes, key=lambda p: (counts[p.id], p.name), default=None)
    if chosen is None:
        return PageProcess(process_id=None, stages=[], reactions=[])
    stages = sorted((s for s in records.process.stages if s.process_id == chosen.id), key=lambda s: s.ordinal)
    shown = [_stored_stage(stage, records.process, (visible, differ)) for stage in stages]
    return PageProcess(process_id=chosen.id, stages=[stage for stage in shown if stage], reactions=[])


def _stored_stage(
    stage: StageRecord, records: ProcessRecords, shown: tuple[Visible, Sequence[DifferRow]]
) -> PageStage | None:
    visible, differ = shown
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
        differ=_stage_differ([*claims, *(t.claim_id for t in timing)], differ),
    )


def _curated_process(
    curated: CuratedPage, records: ProcessRecords, shown: tuple[Visible, Sequence[DifferRow]]
) -> PageProcess:
    visible, differ = shown
    rows = {stage.id: stage for stage in records.stages if stage.process_id == curated.process_id}
    names: dict[uuid.UUID, ItemNames] = {
        item.material_id: (item.local_names, item.botanical_name, item.pubchem_cid)
        for item in curated.materials
    }
    names.update((item.material_id, (item.local_names, None, None)) for item in curated.tools)
    entries = sorted(
        (entry for entry in curated.stages if entry.stage_id in rows), key=lambda e: rows[e.stage_id].ordinal
    )
    stages = [
        _curated_stage(entry, rows[entry.stage_id], records, (visible, names, differ)) for entry in entries
    ]
    unstaged = [_index_reaction(item, visible) for item in curated.reactions if item.reaction_id is None]
    return PageProcess(
        process_id=curated.process_id,
        stages=[stage for stage in stages if stage],
        reactions=[reaction for reaction in unstaged if reaction],
    )


def _curated_stage(
    entry: IndexStage,
    stage: StageRecord,
    records: ProcessRecords,
    shown: tuple[Visible, Mapping[uuid.UUID, ItemNames], Sequence[DifferRow]],
) -> PageStage | None:
    visible, names, differ = shown
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
        differ=_stage_differ([*claims, *(t.claim_id for t in timing)], differ),
    )


def _stage_differ(claim_ids: Sequence[uuid.UUID], differ: Sequence[DifferRow]) -> list[str]:
    own = set(claim_ids)
    return [row.key for row in differ if own.intersection(row.claim_ids)]


def _items(
    records: ProcessRecords, stage_id: uuid.UUID, visible: Visible, names: Mapping[uuid.UUID, ItemNames]
) -> tuple[list[StageItem], list[StageItem]]:
    materials: list[StageItem] = []
    tools: list[StageItem] = []
    for material in sorted(records.materials, key=lambda m: (m.role, m.name.casefold(), str(m.id))):
        claims = visible.ranked(material.claim_ids)
        if material.stage_id != stage_id or material.material_id is None or not claims:
            continue
        compound = material.compound.pubchem_cid if material.compound else None
        local, botanical, cid = names.get(material.material_id, ([], None, compound))
        item = StageItem(
            id=material.material_id,
            name=material.name,
            kind=material.kind,
            role=material.role,
            local_names=local,
            botanical_name=botanical,
            pubchem_cid=cid,
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
