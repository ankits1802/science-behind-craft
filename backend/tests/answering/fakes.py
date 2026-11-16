import uuid
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from typing import Any

from app.composer.composer import ModelComposer
from app.models import ClaimSource, Source
from app.research.composition import ComposedAnswer
from app.research.crafts import CraftCandidate, CraftQuery, CraftResolution, MatchReason
from app.research.evidence_pack import EvidencePack
from app.research.planning import PlanRequest
from app.research.stream import ResearchProgress, event_stream
from app.research.write_back import WriteBackResult
from app.retrieval.indexing import EmbeddedCounts
from app.services import knowledge_view
from app.services.answer_events import CitedClaims, cited_claims
from app.services.answering import AnswerAsk, AnswerPipeline, KeptAnswer, answer_question
from app.services.research_write_back import StoredResearch, sentence_claim_ids
from app.services.write_back_plan import write_back_plan

from ..composer.fixtures import ALUM_CLAIM_ID, GUESS_CLAIM_ID, pack
from ..planner.fakes import FakeModel
from ..research.fixtures import AJRAKH

ANSWER_ID = uuid.UUID("0b1c2d3e-4f50-4617-8293-a4b5c6d7e8f9")
WRITTEN_LAKE_ID = uuid.UUID("6c1e0f2a-3b4d-4e5f-8a9b-0c1d2e3f4a5b")
WRITTEN_WASH_ID = uuid.UUID("8d2f1a3b-4c5e-4f60-9b1c-2d3e4f5a6b7c")
BOOK_ID = uuid.UUID("1a2b3c4d-0000-4000-8000-000000000001")
LAKE_ID = uuid.UUID("1a2b3c4d-0000-4000-8000-000000000002")
WEB_ID = uuid.UUID("1a2b3c4d-0000-4000-8000-000000000003")

BOOK = Source(
    id=BOOK_ID,
    kind="BOOK",
    title="Ajrakh: the printed cloth of Kutch",
    authors=["A. Author"],
    year=2016,
    doi=None,
    url=None,
    publisher="Mapin",
    licence=None,
    attribution=None,
    reliability="A",
)
LAKE = Source(
    id=LAKE_ID,
    kind="PAPER",
    title="Alizarin lakes on cotton",
    authors=["A. Author"],
    year=2019,
    doi="10.1000/lake",
    url="https://doi.org/10.1000/lake",
    publisher="Journal of Dye Chemistry",
    licence="CC BY 4.0",
    attribution=None,
    reliability="B",
)
WEB = Source(
    id=WEB_ID,
    kind="WEB_PAGE",
    title="Ajrakh fastness notes",
    authors=[],
    year=None,
    doi=None,
    url="https://crafts.example.org/ajrakh",
    publisher=None,
    licence=None,
    attribution=None,
    reliability="C",
)


def stored_view(
    claim_id: uuid.UUID, text: str, level: str, cite: tuple[int, Source, str | None, str | None]
) -> knowledge_view.ClaimView:
    number, source, quote, locator = cite
    row = ClaimSource(
        id=uuid.UUID(f"c0000000-0000-4000-8000-{number:012d}"),
        claimId=claim_id,
        sourceId=source.id,
        quote=quote,
        locator=locator,
    )
    return knowledge_view.ClaimView(
        claim_id, text, level, "MATERIAL", None, citations=[knowledge_view.citation(row, level)]
    )


VIEWS = (
    stored_view(
        ALUM_CLAIM_ID,
        "Alum is the mordant that binds alizarin to cotton in Ajrakh.",
        "REVIEWED",
        (1, BOOK, "Alum is the mordant", "p. 41"),
    ),
    stored_view(
        WRITTEN_LAKE_ID,
        "Mordant baths held 8 g/L alum and were heated to 60 °C.",
        "PROVISIONAL",
        (2, LAKE, "Mordanting baths of 8 g/L alum were heated to 60 °C", None),
    ),
    stored_view(
        WRITTEN_WASH_ID,
        "The red lake withstood 20 washes.",
        "PROVISIONAL",
        (3, WEB, "the lake withstood 20 washes", None),
    ),
    stored_view(
        GUESS_CLAIM_ID,
        "Lime in the wash water may brighten the red.",
        "HYPOTHESIS",
        (4, BOOK, None, None),
    ),
)
SOURCES = {BOOK_ID: BOOK, LAKE_ID: LAKE, WEB_ID: WEB}
WRITTEN_IDS = (WRITTEN_LAKE_ID, WRITTEN_WASH_ID)


def resolved(craft: Any = AJRAKH) -> CraftResolution:
    reason = MatchReason(kind="EXACT_NAME", matched=craft.name, score=1.0)
    return CraftResolution(
        status="RESOLVED",
        craft=craft,
        candidates=[CraftCandidate(craft=craft, score=1.0, reasons=[reason])],
        normalised="kutch ajrakh",
        script="Latn",
    )


@dataclass
class FakeStore:
    stored: CitedClaims = field(default_factory=CitedClaims)
    kept: list[tuple[AnswerAsk, EvidencePack, ComposedAnswer]] = field(default_factory=list)
    asked_for: list[list[uuid.UUID]] = field(default_factory=list)

    async def stored_claims(self, craft_slug: str, question: str, mode: str) -> CitedClaims:
        assert (craft_slug, mode) == (AJRAKH.slug, "VERIFIED")
        return self.stored

    async def keep(self, ask: AnswerAsk, pack: EvidencePack, answer: ComposedAnswer) -> KeptAnswer:
        self.kept.append((ask, pack, answer))
        plan = write_back_plan(pack, answer, found_by="ANSWER", answer_id=ANSWER_ID)
        results = tuple(
            WriteBackResult(dedupe_key=claim.dedupe_key, claim_id=claim_id, created=True)
            for claim, claim_id in zip(plan.claims, WRITTEN_IDS, strict=False)
        )
        stored = StoredResearch(
            source_ids=(),
            results=results,
            skipped=plan.skipped,
            embedded=EmbeddedCounts(claims=0, chunks=0),
            sentence_keys=plan.sentence_keys,
        )
        return KeptAnswer(answer_id=ANSWER_ID, claims_of=sentence_claim_ids(answer, stored))

    async def cited(self, claim_ids: Iterable[uuid.UUID]) -> CitedClaims:
        wanted = list(claim_ids)
        self.asked_for.append(wanted)
        return cited_claims([view for view in VIEWS if view.id in wanted], SOURCES)


@dataclass
class FakeResearch:
    pack: EvidencePack = field(default_factory=pack)
    steps: Sequence[tuple[str, int]] = (("SEARCHING_STORED", 1), ("RESEARCHING", 2), ("READING", 4))
    requests: list[PlanRequest] = field(default_factory=list)
    failure: Exception | None = None

    async def __call__(self, request: PlanRequest, progress: ResearchProgress) -> EvidencePack:
        self.requests.append(request)
        for step, count in self.steps:
            await progress(step, count)
        if self.failure is not None:
            raise self.failure
        return self.pack


def pipeline(
    *,
    resolution: CraftResolution | Exception | None = None,
    research: FakeResearch | None = None,
    replies: Sequence[str] = (),
    store: FakeStore | None = None,
) -> AnswerPipeline:
    outcome = resolved() if resolution is None else resolution

    async def resolve(query: CraftQuery) -> CraftResolution:
        if isinstance(outcome, Exception):
            raise outcome
        return outcome

    return AnswerPipeline(
        resolve=resolve,
        research=research or FakeResearch(),
        compose=ModelComposer(model=FakeModel(list(replies))).compose,
        store=store or FakeStore(),
    )


async def streamed(ask: AnswerAsk, answer_pipeline: AnswerPipeline) -> str:
    frames = event_stream(lambda emit: answer_question(ask, answer_pipeline, emit))
    return "".join([frame async for frame in frames])
