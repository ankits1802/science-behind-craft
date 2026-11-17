from __future__ import annotations

import dataclasses
import json
import uuid
from collections.abc import Mapping, Sequence
from functools import cache
from typing import Any

from app.research.blocks import ExplainerSentence, ProseBlock
from app.research.planning import PlanRequest
from app.research.sections import SectionSpec
from app.science.records import (
    CompoundRecord,
    MaterialRecord,
    ProcessRecord,
    ProcessRecords,
    ReactionRecord,
    SpeciesRecord,
    StageRecord,
)
from app.services.answer_events import CitedClaims
from app.services.builder_interface import BuildAsk, BuilderTools
from app.services.claim_seed import load_seed_claims, seed_id
from app.services.craft_matter import CraftMatter, GlossaryTerm, MaterialRows
from app.services.knowledge_view import ClaimView
from app.services.science_seed import load_science_seed, science_seed_plan
from app.services.what_if_evidence import Relationship, WhatIfEvidence

from ..contracts.phase_c_golden import phase_c_blocks
from ..place.fixtures import no_session
from ..planner.fakes import FakeModel
from ..science.golden_process import (
    CRAFT,
    PROCESS_ID,
    RED,
    citation_id,
    claim_id,
    known_claim,
    known_source,
    seed_rows,
    stage_id,
)

WHAT_IF = "s2.b1"
MADDER_CONCEPT = "ie:ajrakh.material.madder"
ALIZARIN_CONCEPT = "ie:ajrakh.material.synthetic-alizarin"
WASH_FAST = "inf:block-printing:wash_fast_red"
CONTRAST = "seed-9f1f03372efe28f1a53a"
TAPANO = "seed-32e7a43af292f11fd3b8"
SHIFT = "seed-31a89c0b1e7bdd4f1ac4"
MADDER_ROOTS = "seed-bd5ef6022d643b22c6dd"
MADDER_WITH_INDIGO = "seed-2976ed9ba77919f34967"
SYNTHESISED = "seed-5bbd031c8cc0abd3b6b9"
ICI_POWDER = "seed-b137eb0c1671ed8f12df"
RED_STAGE = "seed-b14a93745f3a652197c0"
MADDER_OR_AL = "seed-03864cb3c264079f0e1b"
LAKE_MECHANISM = "seed-0484b9bf06c14eb12785"
TAMARIX = "seed-83bff46ae01c13e9806c"
WASHING_HYPOTHESIS = "seed-8d93691e6111ff665632"
MADDER_ID = uuid.UUID("f688cdba-8a3c-5af9-847f-1a91998e0d52")
ALIZARIN_ID = uuid.UUID("02a0d0b9-ae5d-571f-87ae-fe50175c8df2")
ALIZARIN_LAKE = uuid.UUID("65916ac6-7a8e-57c9-baf6-6b0ba5f684da")
AL_ROOT_ID = uuid.uuid5(uuid.NAMESPACE_URL, "test-what-if/material/al-root")
AL_ROOT_USE = uuid.uuid5(uuid.NAMESPACE_URL, "test-what-if/stage-material/al-root")
RED_STAGE_NAME = "Red dyeing (rang) with madder or alizarin"
TERMS = {
    MADDER_ID: (GlossaryTerm("indian-madder", "Indian madder", (), ("majith", "majeeta"), None),),
    ALIZARIN_ID: (
        GlossaryTerm("synthetic-alizarin", "Synthetic alizarin", (), (), None),
        GlossaryTerm("alizarin", "Alizarin", (), (), None),
    ),
    AL_ROOT_ID: (GlossaryTerm("al-root", "Al root", (), ("al",), None),),
}
FIXTURE_REPLY = {
    "input": "i1",
    "changed": "Red dye",
    "options": [
        {"option": "i1.o1", "outcomes": ["i1.o1.e1", "i1.o1.e2"]},
        {"option": "i1.o2", "outcomes": ["i1.o2.e3", "i1.o2.e6"]},
    ],
}


def golden_what_if() -> dict[str, Any]:
    return phase_c_blocks()[WHAT_IF]


def concept(key: str) -> uuid.UUID:
    return seed_id("concept", key)


@cache
def _plan() -> Any:
    return science_seed_plan(load_science_seed(), load_seed_claims())


def concept_claim_keys(concept_key: str) -> list[str]:
    rows = seed_rows()["claims"].values()
    return [row["id"] for row in rows if row["subjectType"] == "CONCEPT" and row["subjectKey"] == concept_key]


def red_records(*, al_root: bool = True) -> ProcessRecords:
    red = stage_id(RED)
    uses = [_seeded_use(row) for row in _plan().rows["stageMaterials"] if row["stageId"] == red]
    if al_root:
        uses.append(MaterialRecord(AL_ROOT_USE, red, "Al root", "DYE", "DYE", None, None, (), AL_ROOT_ID))
    stage_claims = (claim_id(RED_STAGE), claim_id(MADDER_OR_AL))
    wanted = {*stage_claims, *(claim for use in uses for claim in use.claim_ids)}
    wanted |= {claim_id(key) for key, _ in _lake_citations()}
    keys = {claim_id(key): key for key in seed_rows()["claims"]}
    return ProcessRecords(
        craft=CRAFT,
        processes=(ProcessRecord(PROCESS_ID, "Seed process", "seed_claims"),),
        stages=(StageRecord(red, PROCESS_ID, 11, RED_STAGE_NAME, "DYE", stage_claims),),
        materials=tuple(uses),
        reactions=(_alizarin_lake(),),
        conditions=(),
        claims={claim: known_claim(keys[claim]) for claim in wanted},
        sources={str(seed_id("source", key)): known_source(key) for key in seed_rows()["sources"]},
    )


def red_matter(*, al_root: bool = True) -> CraftMatter:
    return matter_of(red_records(al_root=al_root))


def two_stage_matter() -> CraftMatter:
    records = red_records()
    again = uuid.uuid5(uuid.NAMESPACE_URL, "test-what-if/stage/second-red")
    stage = dataclasses.replace(records.stages[0], id=again, ordinal=12, name="Second red dyeing")
    uses = tuple(
        dataclasses.replace(
            use, id=uuid.uuid5(uuid.NAMESPACE_URL, f"test-what-if/second/{use.id}"), stage_id=again
        )
        for use in records.materials
    )
    return matter_of(
        dataclasses.replace(records, stages=(*records.stages, stage), materials=(*records.materials, *uses))
    )


def matter_of(records: ProcessRecords) -> CraftMatter:
    grouped: dict[uuid.UUID, list[MaterialRecord]] = {}
    for use in records.materials:
        grouped.setdefault(use.material_id or use.id, []).append(use)
    return CraftMatter(
        records=records,
        materials=tuple(
            MaterialRows(material_id, tuple(found), TERMS.get(material_id, ()))
            for material_id, found in grouped.items()
        ),
        compounds={},
        record_sources={},
    )


SEEDED_RELATIONS = (
    (CONTRAST, "CONTRASTS_WITH", MADDER_CONCEPT, ALIZARIN_CONCEPT),
    (TAPANO, "DEPENDS_ON", "ie:ajrakh.process_stage.tapano", MADDER_CONCEPT),
    (SHIFT, "ENABLES", ALIZARIN_CONCEPT, "ie:ajrakh.historical_context.synthetic-dye-shift-and-revival"),
)
HYPOTHESIS_RELATION = (WASHING_HYPOTHESIS, "CAUSES", ALIZARIN_CONCEPT, WASH_FAST)


def evidence(*, hypothesis: bool = False) -> WhatIfEvidence:
    rows = [*SEEDED_RELATIONS, *((HYPOTHESIS_RELATION,) if hypothesis else ())]
    relationships = [
        Relationship(claim_id(key), relation, frozenset({concept(source), concept(target)}))
        for key, relation, source, target in rows
    ]
    owned = {key: concept_claim_keys(key) for key in (MADDER_CONCEPT, ALIZARIN_CONCEPT)}
    keys = [CONTRAST, TAPANO, SHIFT, WASHING_HYPOTHESIS]
    keys += [found_key for found in owned.values() for found_key in found]
    return WhatIfEvidence(
        relationships=tuple(sorted(relationships, key=lambda found: found.claim_id)),
        concept_claims={
            concept(key): tuple(sorted(claim_id(found) for found in found_keys))
            for key, found_keys in owned.items()
        },
        views={claim_id(key): view(key) for key in keys},
        sources={str(seed_id("source", key)): known_source(key) for key in seed_rows()["sources"]},
    )


def view(key: str) -> ClaimView:
    found = known_claim(key)
    return ClaimView(
        id=found.id,
        text=found.text,
        level=found.level,
        concept_type="MATERIAL",
        concept_id=None,
        citations=[c.model_dump(mode="json", by_alias=True) for c in found.citations],
    )


def sentence(sentence_id: str, key: str) -> ExplainerSentence:
    found = known_claim(key)
    return ExplainerSentence(
        id=sentence_id, text=found.text, level=found.level, citations=list(found.citations), terms=[]
    )


def red_ask(*, discipline: str = "PROCESS", keys: Sequence[str] = (MADDER_ROOTS, SYNTHESISED)) -> BuildAsk:
    prose = ProseBlock(
        id="s2.b1",
        kind="prose",
        version=1,
        reuse=None,
        sentences=[sentence(f"s2.b1.{n}", key) for n, key in enumerate(keys, 1)],
    )
    sources = red_records().sources
    cited = CitedClaims(
        views={claim_id(key): view(key) for key in keys},
        sources={
            sid: sources[sid].model_dump(mode="json", by_alias=True) for sid in prose.cited_source_ids()
        },
    )
    request = PlanRequest(question="Why does Ajrakh red use madder or alizarin?", mode="HYBRID", craft=CRAFT)
    spec = SectionSpec(id="s2", discipline=discipline, title="Red dyeing", order=2)
    return BuildAsk(uuid.UUID(int=2), spec, request, (prose,), cited)


def what_if_model(*replies: Mapping[str, Any] | str) -> FakeModel:
    texts = [reply if isinstance(reply, str) else json.dumps(reply) for reply in replies or (FIXTURE_REPLY,)]
    return FakeModel(texts)


def what_if_tools(model: FakeModel | None = None) -> BuilderTools:
    return BuilderTools(
        sessions=no_session, live=None, plan_model=model or what_if_model(), compose_model=None
    )


def _seeded_use(row: Mapping[str, Any]) -> MaterialRecord:
    material = next(found for found in _plan().rows["materials"] if found["id"] == row["materialId"])
    compound = next(
        (found for found in _plan().rows["compounds"] if found["id"] == material["compoundId"]), None
    )
    concept_key = next(key for key in _concept_keys() if concept(key) == material["conceptId"])
    owned = [claim_id(key) for key in concept_claim_keys(concept_key)]
    return MaterialRecord(
        id=row["id"],
        stage_id=row["stageId"],
        name=material["name"],
        kind=material["kind"],
        role=row["role"],
        quantity_text=None,
        compound=None
        if compound is None
        else CompoundRecord(compound["id"], compound["name"], compound["formula"], None),
        claim_ids=(row["claimId"], *owned),
        material_id=material["id"],
        concept_id=material["conceptId"],
    )


@cache
def _concept_keys() -> tuple[str, ...]:
    return tuple(row["key"] for row in load_seed_claims()["concepts"])


def _lake_citations() -> list[tuple[str, int]]:
    science = load_science_seed()
    lake = next(r for r in science["reactions"] if r["stage"] == RED and r["key"] == "alizarin-lake")
    return [(key, index) for key, index in lake["citations"]]


def _alizarin_lake() -> ReactionRecord:
    row = next(found for found in _plan().rows["reactions"] if found["id"] == ALIZARIN_LAKE)
    return ReactionRecord(
        id=row["id"],
        stage_id=row["stageId"],
        ordinal=row["ordinal"],
        kind=row["kind"],
        label=row["label"],
        species=tuple(
            SpeciesRecord(
                s["role"], s["formula"], s["name"], uuid.UUID(s["compoundId"]) if s["compoundId"] else None
            )
            for s in row["species"]
        ),
        balanced=row["balanced"],
        coefficients=None,
        checker_version=None,
        delta_h=None,
        citations=tuple((claim_id(key), str(citation_id(key, index))) for key, index in _lake_citations()),
    )
