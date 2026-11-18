from __future__ import annotations

import uuid
from typing import Any

from app.research.blocks_play import SimulationBlock
from app.research.planning import PlanRequest
from app.research.sections import SectionSpec
from app.services.answer_events import CitedClaims
from app.services.builder_interface import BuildAsk
from app.services.chapter_preview import preview_rows
from app.services.craft_matter import CraftMatter
from app.services.craft_page import chapter_context
from app.services.curation_keys import curated_id
from app.services.curation_preview import dossier_records
from app.services.section_blocks import KeptSentence, prose_block

from ..contracts.golden import golden_json
from .fixtures import DraftModel, builder

AJRAKH = "Kutch-Ajrakh"
FAMILY = "Textiles-Based-Craft-Category"
CRAFT_MECHANISM_GOLDEN = "explainer.craft-mechanism.golden.json"
KUT_BLACK = curated_id(AJRAKH, "C078")
QUESTION = "How does kut turn black on the harde-treated cloth of ajrakh?"
SECTION = SectionSpec(id="s1", discipline="CHEMISTRY", title="The chemistry", order=1)
ANSWER = uuid.UUID("5f0c8e2a-9d1b-5c3e-8a7f-1b2c3d4e5f60")


def craft_mechanism_golden() -> dict[str, Any]:
    return golden_json(CRAFT_MECHANISM_GOLDEN)


def recorded_draft() -> dict[str, Any]:
    block = craft_mechanism_golden()["block"]
    return {
        "build": True,
        "concept": block["concept"],
        "title": block["title"],
        "grounds": ["s1"],
        "reactions": ["r1"],
        "values": [],
        "html": block["html"],
    }


def ajrakh_matter_and_ask() -> tuple[CraftMatter, BuildAsk]:
    records = dossier_records(AJRAKH)
    ctx = chapter_context(records, preview_rows(records, family=FAMILY, inputs=None))
    (view,) = [view for view in records.views if view.id == KUT_BLACK]
    cited_ids = {citation["sourceId"] for citation in view.citations}
    sources = {sid: records.sources[sid].model_dump(mode="json", by_alias=True) for sid in cited_ids}
    cited = CitedClaims(views={view.id: view}, sources=sources)
    prose = prose_block("s1.b1", [KeptSentence(view.text, (view.id,), (), False)], cited)
    request = PlanRequest(question=QUESTION, mode="HYBRID", craft=records.process.craft, depth="EXPERT")
    return ctx.matter(), BuildAsk(ANSWER, SECTION, request, (prose,), cited)


async def built_craft_mechanism(draft: dict[str, Any]) -> tuple[SimulationBlock, dict[str, Any]]:
    matter, ask = ajrakh_matter_and_ask()
    built = await builder(DraftModel([]), matter=matter, explainer=DraftModel([draft])).build(ask)
    (block,) = built.blocks
    assert isinstance(block, SimulationBlock)
    known = {**ask.cited.sources, **built.sources}
    sources = [known[sid] for sid in dict.fromkeys(c.source_id for c in block.citations())]
    return block, {
        "schemaVersion": 1,
        "claimId": str(KUT_BLACK),
        "block": block.model_dump(mode="json", by_alias=True),
        "sources": sources,
    }
