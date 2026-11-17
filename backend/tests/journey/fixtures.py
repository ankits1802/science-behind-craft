from __future__ import annotations

import dataclasses
import json
import uuid
from collections.abc import Mapping, Sequence
from typing import Any

from app.geo.records import DatasetRecord
from app.research.blocks import ExplainerSentence, ProseBlock
from app.research.blocks_place import DistrictRef
from app.research.datasets import DatasetRef
from app.research.media_refs import MediaRef
from app.research.planning import PlanRequest
from app.research.sections import SectionSpec
from app.science.records import KnownClaim
from app.services.answer_events import CitedClaims
from app.services.builder_interface import BuildAsk, BuilderTools
from app.services.claim_seed import seed_id
from app.services.craft_matter import CraftMatter
from app.services.knowledge_view import ClaimView
from app.services.media_ref_store import StoredPicture
from app.services.zoom_story import ZoomGround

from ..contracts.explainer_golden import golden_json
from ..contracts.phase_c_golden import phase_c, phase_c_blocks
from ..matter.fixtures import matter
from ..place.fixtures import no_session
from ..place.season_supply_fixtures import claims_of
from ..planner.fakes import FakeModel
from ..research.fixtures import AJRAKH
from ..science.golden_process import ALIZARIN

ZOOM = "s3.b1"
TIMELINE = "s4.b1"
FUSTAT_POINT = ("Q839456", 30.005, 31.2375)
TIMELINE_REPLY = {
    "points": [
        {"statement": "c3", "place": "Ajrakhpur", "years": "y1"},
        {"statement": "c1", "place": "Fustat", "years": "y1"},
        {"statement": "c2", "place": "Dhamadka", "years": "y2"},
    ],
    "routes": [{"statement": "c4", "start": "Sindh", "end": "Kutch", "years": "y2"}],
}


def golden_zoom() -> dict[str, Any]:
    return phase_c_blocks()[ZOOM]


def golden_timeline() -> dict[str, Any]:
    return phase_c_blocks()[TIMELINE]


def renamed(block: Mapping[str, Any], old: str, new: str) -> dict[str, Any]:
    return json.loads(json.dumps(block).replace(f'"{old}', f'"{new}'))


def zoom_claims() -> list[KnownClaim]:
    return claims_of([level["sentence"] for level in golden_zoom()["levels"]])


def timeline_claims() -> list[KnownClaim]:
    block = golden_timeline()
    return claims_of([item["sentence"] for item in (*block["points"], *block["routes"])])


def phase_c_ask(claims: Sequence[KnownClaim], *, discipline: str, section_id: str) -> BuildAsk:
    sentences = [
        ExplainerSentence(
            id=f"{section_id}.b1.{n}", text=c.text, level=c.level, citations=list(c.citations), terms=[]
        )
        for n, c in enumerate(claims, start=1)
    ]
    prose = ProseBlock(id=f"{section_id}.b1", kind="prose", version=1, reuse=None, sentences=sentences)
    sources = {source["id"]: source for source in phase_c()["sources"]}
    cited = CitedClaims(
        views={c.id: _view(c) for c in claims},
        sources={sid: sources[sid] for sid in prose.cited_source_ids() if sid in sources},
    )
    request = PlanRequest(question="How did Ajrakh come to Kutch?", mode="HYBRID", craft=AJRAKH)
    spec = SectionSpec(id=section_id, discipline=discipline, title="Story", order=3)
    return BuildAsk(uuid.UUID(int=7), spec, request, (prose,), cited)


def boundary_dataset() -> DatasetRef:
    return DatasetRef.model_validate(golden_zoom()["datasets"][0])


def boundary_record() -> DatasetRecord:
    found = boundary_dataset()
    return DatasetRecord(
        code=found.code,
        title=found.title,
        publisher=found.publisher,
        edition=found.edition,
        period=found.period,
        native_resolution=found.native_resolution,
        licence=found.licence,
        licence_url=found.licence_url,
        attribution=found.attribution,
        citation=found.citation,
        url=found.url,
    )


def kachchh() -> DistrictRef:
    return DistrictRef.model_validate(golden_zoom()["levels"][0]["district"])


def workshop_media() -> MediaRef:
    pictures = golden_json("explainer.document.golden.json")["sections"][0]["blocks"][1]["items"]
    return MediaRef.model_validate(pictures[0]["media"])


def cloth_link_card() -> dict[str, Any]:
    pictures = golden_json("explainer.document.golden.json")["sections"][0]["blocks"][1]["items"]
    return pictures[1]["media"]


def zoom_ground_of(*, pictures: bool = True, boundary: bool = True) -> ZoomGround:
    district, workshop, _ = zoom_claims()
    stored = (StoredPicture(workshop_media(), workshop.id, "TEXT"),) if pictures else ()
    return ZoomGround(
        districts=(kachchh(),),
        boundary=boundary_dataset() if boundary else None,
        claims=(district,),
        sources={},
        pictures=stored,
    )


def zoom_matter() -> CraftMatter:
    found = matter()
    seeded = seed_id("compound", "alizarin")
    alizarin = dataclasses.replace(found.compounds[ALIZARIN], id=seeded)
    others = {cid: row for cid, row in found.compounds.items() if cid != ALIZARIN}
    return dataclasses.replace(found, compounds={seeded: alizarin, **others})


def timeline_model(*replies: Mapping[str, Any]) -> FakeModel:
    return FakeModel([json.dumps(reply) for reply in replies or (TIMELINE_REPLY,)])


def journey_tools(model: FakeModel | None = None) -> BuilderTools:
    return BuilderTools(
        sessions=no_session, live=None, plan_model=model or timeline_model(), compose_model=None
    )


def _view(claim: KnownClaim) -> ClaimView:
    return ClaimView(
        id=claim.id,
        text=claim.text,
        level=claim.level,
        concept_type="CONCEPT",
        concept_id=None,
        citations=[c.model_dump(mode="json", by_alias=True) for c in claim.citations],
    )
