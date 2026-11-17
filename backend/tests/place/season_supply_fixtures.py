from __future__ import annotations

import json
import uuid
from collections.abc import Mapping, Sequence
from typing import Any

from app.research.blocks import ExplainerSentence, ProseBlock
from app.research.citations import Citation
from app.research.planning import PlanRequest
from app.research.sections import SectionSpec
from app.science.records import KnownClaim, MaterialRecord
from app.services.answer_events import CitedClaims
from app.services.builder_interface import BuildAsk, BuilderTools
from app.services.craft_matter import GlossaryTerm, MaterialRows
from app.services.knowledge_view import ClaimView

from ..contracts.phase_b_golden import phase_b, phase_b_blocks
from ..planner.fakes import FakeModel
from ..research.fixtures import AJRAKH
from .fixtures import no_session

SEASONS = "s3.b1"
SUPPLY = "s6.b1"
GI_JOURNAL = "d0f53ee9-4b97-5df7-a367-686957bdb7c8"
MONSOON_HUMIDITY = "Monsoon humidity"
INDIGO_MATERIAL = uuid.UUID("e3302885-722e-57cf-ad15-6f0c41b1a678")
INDIGO_TERM = GlossaryTerm("indigo", "Indigo", (), ("gali", "nil"), None)
GOLDEN_LINKS = {
    "links": [
        {"statement": "c1", "material": "m1", "materialWords": "", "origin": "Shikarpur"},
        {"statement": "c1", "material": "m1", "materialWords": "", "origin": "Dhamadka"},
        {"statement": "c2", "material": "none", "materialWords": "Blocks", "origin": "Pethapur"},
    ]
}


def golden_seasons() -> dict[str, Any]:
    return phase_b_blocks()[SEASONS]


def golden_supply() -> dict[str, Any]:
    return phase_b_blocks()[SUPPLY]


def claims_of(sentences: Sequence[Mapping[str, Any]]) -> list[KnownClaim]:
    found: dict[uuid.UUID, KnownClaim] = {}
    for sentence in sentences:
        citations = tuple(Citation.model_validate(c) for c in sentence["citations"])
        claim_id = uuid.UUID(citations[0].claim_id)
        found.setdefault(claim_id, KnownClaim(claim_id, sentence["text"], sentence["level"], citations))
    return list(found.values())


def season_claims() -> list[KnownClaim]:
    return claims_of([row["sentence"] for row in golden_seasons()["rows"]])


def supply_claims() -> list[KnownClaim]:
    return claims_of([link["sentence"] for link in golden_supply()["links"]])


def written_claim(key: str, text: str, quote: str) -> KnownClaim:
    claim_id = uuid.uuid5(uuid.NAMESPACE_URL, f"test-seasons/claim/{key}")
    citation = Citation(
        id=str(uuid.uuid5(uuid.NAMESPACE_URL, f"test-seasons/citation/{key}")),
        claim_id=str(claim_id),
        source_id=GI_JOURNAL,
        quote=quote,
        locator="PDF p. 5",
        context=None,
        evidence="QUOTED",
        level="PROVISIONAL",
    )
    return KnownClaim(claim_id, text, "PROVISIONAL", (citation,))


def concept_of(claim: KnownClaim) -> uuid.UUID:
    return uuid.uuid5(uuid.NAMESPACE_URL, f"test-seasons/concept/{claim.id}")


def section_ask(
    claims: Sequence[KnownClaim], *, discipline: str = "CLIMATE", section_id: str = "s3", craft: bool = True
) -> BuildAsk:
    sentences = [
        ExplainerSentence(
            id=f"{section_id}.b1.{n}", text=c.text, level=c.level, citations=list(c.citations), terms=[]
        )
        for n, c in enumerate(claims, start=1)
    ]
    prose = ProseBlock(id=f"{section_id}.b1", kind="prose", version=1, reuse=None, sentences=sentences)
    sources = {source["id"]: source for source in phase_b()["sources"]}
    cited = CitedClaims(
        views={c.id: _view(c) for c in claims},
        sources={sid: sources[sid] for sid in prose.cited_source_ids() if sid in sources},
    )
    request = PlanRequest(
        question="When is Ajrakh printed in Kutch?", mode="HYBRID", craft=AJRAKH if craft else None
    )
    spec = SectionSpec(id=section_id, discipline=discipline, title="Climate", order=3)
    return BuildAsk(uuid.UUID(int=3), spec, request, (prose,), cited)


def indigo_rows(claim: KnownClaim) -> MaterialRows:
    use = MaterialRecord(
        id=uuid.uuid5(uuid.NAMESPACE_URL, "test-supply/stage-material/indigo"),
        stage_id=uuid.uuid5(uuid.NAMESPACE_URL, "test-supply/stage/indigo-dyeing"),
        name="Indigo (natural Indigofera tinctoria or synthetic)",
        kind="DYE",
        role="DYE",
        quantity_text=None,
        compound=None,
        claim_ids=(claim.id,),
        material_id=INDIGO_MATERIAL,
        concept_id=None,
    )
    return MaterialRows(INDIGO_MATERIAL, (use,), (INDIGO_TERM,))


def links_model(*replies: Mapping[str, Any]) -> FakeModel:
    return FakeModel([json.dumps(reply) for reply in replies or (GOLDEN_LINKS,)])


def season_tools(model: FakeModel | None = None) -> BuilderTools:
    return BuilderTools(sessions=no_session, live=None, plan_model=model or links_model(), compose_model=None)


def _view(claim: KnownClaim) -> ClaimView:
    return ClaimView(
        id=claim.id,
        text=claim.text,
        level=claim.level,
        concept_type="CONCEPT",
        concept_id=concept_of(claim),
        citations=[c.model_dump(mode="json", by_alias=True) for c in claim.citations],
    )
