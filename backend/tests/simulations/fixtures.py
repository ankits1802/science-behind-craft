from __future__ import annotations

import json
import uuid
from collections.abc import Collection, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from app.research.blocks import ImagesBlock
from app.research.blocks_play import SimulationBlock
from app.research.crafts import CraftRef
from app.research.knowledge_pieces import KnowledgePiece, PieceSlot, knowledge_piece, piece_slot
from app.research.planning import PlanRequest
from app.research.sections import SectionSpec
from app.research.structured import StructuredReply
from app.science.mechanisms import Concept
from app.services.answer_events import CitedClaims
from app.services.builder_interface import BuildAsk, BuilderTools
from app.services.craft_matter import CraftMatter
from app.services.knowledge_view import ClaimView
from app.services.section_blocks import KeptSentence, prose_block
from app.services.simulation_builder import SimulationBuilder

from ..contracts.phase_c_golden import corpus, phase_c, phase_c_blocks
from ..research.fixtures import AJRAKH

OPUS = "claude-opus-5-5"
BUILT_AT = datetime(2026, 11, 18, 10, 30, tzinfo=UTC)
STORED_AT = datetime(2026, 11, 17, 9, 0, tzinfo=UTC)
QUESTION = "Why are the Ajrakh printers of Kutch running out of water?"
WATER_CLAIM = uuid.UUID("00885460-e0ce-5a6e-905c-28da38a06a16")
WATER_TEXT = (
    "Water levels have been going down by 10-15 feet every year; "
    "no comprehensive water management plan has emerged."
)
WATER_STATED = "going down by 10-15 feet every year"
SECTION = SectionSpec(id="s1", discipline="GEOGRAPHY", title="Geography and water", order=1)
CONCEPT = "Falling water table"
TITLE = "How fast the water table falls"
LOW_LABEL = "Yearly fall of the water level, lower figure"
HIGH_LABEL = "Yearly fall of the water level, higher figure"


def golden_simulation() -> dict[str, Any]:
    return phase_c_blocks()["s1.b1"]


def water_citation() -> dict[str, Any]:
    return golden_simulation()["values"][0]["citations"][0]


def water_view(level: str = "PROVISIONAL") -> ClaimView:
    return ClaimView(WATER_CLAIM, WATER_TEXT, level, "CONCEPT", None, citations=[water_citation()])


def cited(views: Sequence[ClaimView] | None = None) -> CitedClaims:
    shown = list(views) if views is not None else [water_view()]
    sources = {source["id"]: source for source in phase_c()["sources"]}
    wanted = {citation["sourceId"] for view in shown for citation in view.citations}
    return CitedClaims(views={view.id: view for view in shown}, sources={i: sources[i] for i in wanted})


def build_ask(views: Sequence[ClaimView] | None = None, *, depth: str = "EXPERT") -> BuildAsk:
    claims = cited(views)
    kept = [KeptSentence(view.text, (view.id,), (), False) for view in claims.views.values()]
    request = PlanRequest(question=QUESTION, mode="HYBRID", craft=AJRAKH, depth=depth)
    return BuildAsk(uuid.uuid4(), SECTION, request, (prose_block("s1.b1", kept, claims),), claims)


def value_choices(*, unit: str = "feet") -> list[dict[str, str]]:
    return [
        {"ref": "v1", "key": "fallLowFeet", "label": LOW_LABEL, "unit": unit},
        {"ref": "v2", "key": "fallHighFeet", "label": HIGH_LABEL, "unit": unit},
    ]


def draft(html: str, **changes: Any) -> dict[str, Any]:
    reply = {"build": True, "concept": CONCEPT, "title": TITLE, "values": value_choices(), "html": html}
    return reply | changes


def accepted_html() -> str:
    return corpus()["accepted"][0]["html"]


@dataclass
class DraftModel:
    replies: list[dict[str, Any]]
    model: str | None = OPUS
    calls: list[dict[str, Any]] = field(default_factory=list)

    async def __call__(self, *, system: str, user: str, schema: Mapping[str, Any]) -> StructuredReply:
        self.calls.append({"system": system, "user": user, "schema": schema})
        reply = self.replies[min(len(self.calls), len(self.replies)) - 1]
        return StructuredReply(text=json.dumps(reply), degraded=False, model=self.model)


@dataclass
class StoredPieces:
    pieces: list[KnowledgePiece] = field(default_factory=list)
    asked: list[tuple[frozenset[uuid.UUID], str]] = field(default_factory=list)

    async def __call__(self, claim_ids: Collection[uuid.UUID], facet: str) -> list[KnowledgePiece]:
        self.asked.append((frozenset(claim_ids), facet))
        return [piece for piece in self.pieces if set(piece.claim_ids) <= set(claim_ids)]


@dataclass
class PictureSearches:
    found: dict[str, ImagesBlock] = field(default_factory=dict)
    asked: list[tuple[str, str, tuple[uuid.UUID, ...]]] = field(default_factory=list)

    async def __call__(self, ask: BuildAsk, concept: Concept, block_id: str) -> ImagesBlock | None:
        self.asked.append((concept.key, " ".join(concept.words), concept.shown_claim_ids))
        block = self.found.get(concept.key)
        return None if block is None else block.model_copy(update={"id": block_id})


async def no_matter(craft: CraftRef) -> CraftMatter | None:
    return None


def builder(
    model: DraftModel,
    stored: StoredPieces | None = None,
    *,
    matter: CraftMatter | None = None,
    pictures: PictureSearches | None = None,
    explainer: DraftModel | None = None,
) -> SimulationBuilder:
    tools = BuilderTools(
        sessions=None, live=None, plan_model=None, compose_model=model, explainer_model=explainer
    )

    async def matter_of(craft: CraftRef) -> CraftMatter | None:
        return matter

    return SimulationBuilder(
        tools,
        stored=stored or StoredPieces(),
        clock=lambda: BUILT_AT,
        matter=matter_of if matter is not None else no_matter,
        pictures=pictures or PictureSearches(),
    )


def golden_block(**changes: Any) -> SimulationBlock:
    return SimulationBlock.model_validate(golden_simulation() | changes)


def stored_simulation(
    block: SimulationBlock | None = None, *, depth: str = "EXPERT", facet: str = "GEOGRAPHY", **changes: Any
) -> KnowledgePiece:
    shown = block or golden_block()
    slot = piece_slot(shown, PieceSlot(None, facet, "water:kachchh", depth))
    piece = knowledge_piece(shown, slot, piece_id=uuid.uuid4(), answer_id=uuid.uuid4(), created_at=STORED_AT)
    return piece.model_copy(update=changes)
