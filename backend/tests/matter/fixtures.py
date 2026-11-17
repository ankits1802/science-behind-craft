from __future__ import annotations

import dataclasses
import json
import uuid
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from app.research.blocks import ExplainerSentence, ProseBlock
from app.research.planning import PlanRequest
from app.research.sections import SectionSpec
from app.research.structured import StructuredReply
from app.research.terms import TermSpan
from app.science.records import CompoundRecord, MaterialRecord
from app.services.answer_events import CitedClaims
from app.services.builder_interface import BuildAsk
from app.services.claim_seed import seed_id
from app.services.compound_lookup import record_source_id
from app.services.craft_matter import CraftMatter, GlossaryTerm, MaterialRows
from app.services.knowledge_view import ClaimView

from ..contracts.phase_b_golden import phase_b
from ..science.golden_process import ALIZARIN, CRAFT, IRON_ACETATE, claim_id, golden_records, known_claim

POTASSIUM_ALUM = seed_id("compound", "potassium-alum")
ALIZARIN_CID = 6293
POTASSIUM_ALUM_CID = 24856
ALIZARIN_RECORD = str(record_source_id(ALIZARIN_CID))
ALUM_RECORD = str(record_source_id(POTASSIUM_ALUM_CID))
ALUM_MATERIAL = "e2c65ac5-52a9-5625-9ed7-ce0d1c1cb19c"
ALUM_OWN_CLAIM = "seed-3b6ee85c9270e4102746"
PA_CLAIM = "seed-d9873cde3faa1e45c9c4"
RED_CLAIM = "seed-b14a93745f3a652197c0"
ALUM_TERM = GlossaryTerm("alum", "alum", (), ("fatakdi", "fitkari", "karam", "Fatakdi"), None)
POTASSIUM_ALUM_TERM = GlossaryTerm("potassium-alum", "Potassium alum", (), (), None)


def material_row(material_id: str) -> uuid.UUID:
    return uuid.uuid5(uuid.NAMESPACE_URL, f"test-matter/material/{material_id}")


def alizarin_record_source() -> dict[str, Any]:
    return next(source for source in phase_b()["sources"] if source["id"] == ALIZARIN_RECORD)


def alum_record_source() -> dict[str, Any]:
    return {
        **alizarin_record_source(),
        "id": ALUM_RECORD,
        "title": f"Potassium Alum (PubChem CID {POTASSIUM_ALUM_CID})",
        "url": f"https://pubchem.ncbi.nlm.nih.gov/compound/{POTASSIUM_ALUM_CID}",
        "attribution": f"PubChem, National Library of Medicine, CID {POTASSIUM_ALUM_CID}",
    }


def compounds(*, alum_linked: bool = False) -> dict[uuid.UUID, CompoundRecord]:
    alum = CompoundRecord(POTASSIUM_ALUM, "Potassium alum", "KAl(SO4)2·12H2O", None, None)
    if alum_linked:
        alum = dataclasses.replace(alum, pubchem_cid=POTASSIUM_ALUM_CID, source_id=uuid.UUID(ALUM_RECORD))
    return {
        ALIZARIN: CompoundRecord(ALIZARIN, "Alizarin", "C14H8O4", ALIZARIN_CID, uuid.UUID(ALIZARIN_RECORD)),
        IRON_ACETATE: CompoundRecord(IRON_ACETATE, "Iron(II) acetate", "Fe(CH3COO)2", None, None),
        POTASSIUM_ALUM: alum,
    }


def matter(*, alum_linked: bool = False) -> CraftMatter:
    records = golden_records()
    known = compounds(alum_linked=alum_linked)
    uses = tuple(_material(use, known) for use in records.materials)
    rows = tuple(
        MaterialRows(
            use.material_id,
            (use,),
            (ALUM_TERM, POTASSIUM_ALUM_TERM) if str(use.id) == ALUM_MATERIAL else (),
        )
        for use in uses
    )
    sources = {ALIZARIN_RECORD: alizarin_record_source()}
    if alum_linked:
        sources[ALUM_RECORD] = alum_record_source()
    return CraftMatter(
        records=dataclasses.replace(records, materials=uses),
        materials=rows,
        compounds=known,
        record_sources=sources,
    )


def _material(use: MaterialRecord, known: Mapping[uuid.UUID, CompoundRecord]) -> MaterialRecord:
    compound = known[POTASSIUM_ALUM] if str(use.id) == ALUM_MATERIAL else None
    return dataclasses.replace(use, material_id=material_row(str(use.id)), compound=compound)


def view(claim: str) -> ClaimView:
    found = known_claim(claim)
    return ClaimView(
        id=found.id,
        text=found.text,
        level=found.level,
        concept_type="PROCESS_STAGE",
        concept_id=None,
        citations=[c.model_dump(mode="json", by_alias=True) for c in found.citations],
    )


def sentence(sentence_id: str, claim: str, terms: list[TermSpan]) -> ExplainerSentence:
    found = known_claim(claim)
    return ExplainerSentence(
        id=sentence_id, text=found.text, level=found.level, citations=list(found.citations), terms=terms
    )


def chemistry_ask(*, discipline: str = "CHEMISTRY", craft: bool = True) -> BuildAsk:
    prose = ProseBlock(
        id="s4.b1",
        kind="prose",
        version=1,
        reuse=None,
        sentences=[
            sentence("s4.b1.1", PA_CLAIM, [TermSpan(text="alum", term_key="alum")]),
            sentence("s4.b1.2", RED_CLAIM, []),
        ],
    )
    sources = golden_records().sources
    cited = CitedClaims(
        views={claim_id(c): view(c) for c in (PA_CLAIM, RED_CLAIM)},
        sources={
            sid: sources[sid].model_dump(mode="json", by_alias=True) for sid in prose.cited_source_ids()
        },
    )
    request = PlanRequest(
        question="Why is alum used in Ajrakh?", mode="HYBRID", craft=CRAFT if craft else None
    )
    spec = SectionSpec(id="s4", discipline=discipline, title="The chemistry", order=4)
    return BuildAsk(uuid.UUID(int=4), spec, request, (prose,), cited)


@dataclass
class CardModel:
    reply: Mapping[str, Any] | str
    calls: list[dict[str, Any]] = field(default_factory=list)

    async def __call__(self, *, system: str, user: str, schema: Mapping[str, Any]) -> StructuredReply:
        self.calls.append({"system": system, "user": user, "schema": schema})
        text = self.reply if isinstance(self.reply, str) else json.dumps(self.reply)
        return StructuredReply(text=text, degraded=False)
