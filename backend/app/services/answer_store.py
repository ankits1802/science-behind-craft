from __future__ import annotations

import uuid
from collections.abc import Iterable

from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.composer.composer import ModelComposer
from app.core.errors import InvalidInput
from app.models import Answer
from app.planner.orchestrator import ResearchPlanner
from app.research.composition import ComposedAnswer
from app.research.crafts import CraftQuery, CraftResolution
from app.research.embedding import TextEmbedder
from app.research.evidence_pack import EvidencePack
from app.research.planning import PlanRequest
from app.research.stream import ResearchProgress
from app.research.structured import StructuredModel
from app.retrieval.hybrid import SessionScopedSearch

from . import knowledge_view
from .answer_events import CitedClaims, cited_claims
from .answering import AnswerAsk, AnswerPipeline, KeptAnswer
from .craft_resolver import CraftIndexStore, DatabaseCraftResolver
from .live_sources import LiveSourcesStore
from .research_write_back import sentence_claim_ids, store_live_research

__all__ = ["SqlAnswerStore", "build_answer_pipeline"]


class SqlAnswerStore:
    def __init__(self, sessions: async_sessionmaker[AsyncSession], *, embed: TextEmbedder) -> None:
        self._sessions = sessions
        self._embed = embed

    async def stored_claims(self, craft_slug: str, question: str, mode: str) -> CitedClaims:
        async with self._sessions() as session:
            craft = await knowledge_view.resolve_craft(session, craft_slug)
            if craft is None:
                raise InvalidInput(f"No craft has the slug {craft_slug!r}")
            views, sources = await knowledge_view.claims_for(session, craft, mode=mode, question=question)
        return cited_claims(views, sources)

    async def keep(self, ask: AnswerAsk, pack: EvidencePack, answer: ComposedAnswer) -> KeptAnswer:
        answer_id = uuid.uuid4()
        async with self._sessions() as session:
            craft = await knowledge_view.resolve_craft(session, pack.plan.craft.slug)
            session.add(
                Answer(
                    id=answer_id,
                    userId=ask.user_id,
                    question=ask.question,
                    language=pack.plan.language,
                    mode=pack.plan.mode,
                    craftId=craft.id if craft else None,
                    plan=pack.plan.model_dump(mode="json", by_alias=True),
                    tiersUsed=list(pack.plan.tiers),
                )
            )
            await session.flush()
            stored = None
            if pack.documents:
                stored = await store_live_research(
                    session, pack, answer, embed=self._embed, found_by="ANSWER", answer_id=answer_id
                )
            claims_of = sentence_claim_ids(answer, stored)
            cited = list(dict.fromkeys(claim for claims in claims_of for claim in claims))
            await session.execute(update(Answer).where(Answer.id == answer_id).values(claimIds=cited))
            await session.commit()
        return KeptAnswer(answer_id=answer_id, claims_of=claims_of)

    async def cited(self, claim_ids: Iterable[uuid.UUID]) -> CitedClaims:
        async with self._sessions() as session:
            views, sources = await knowledge_view.claims_by_id(session, claim_ids)
        return cited_claims(list(views.values()), sources)


def build_answer_pipeline(
    *,
    sessions: async_sessionmaker[AsyncSession],
    index: CraftIndexStore,
    live: LiveSourcesStore,
    plan_model: StructuredModel,
    compose_model: StructuredModel,
    embed: TextEmbedder,
) -> AnswerPipeline:
    async def resolve(query: CraftQuery) -> CraftResolution:
        async with sessions() as session:
            return await DatabaseCraftResolver(session, store=index, embed=embed).resolve(query)

    async def research(request: PlanRequest, progress: ResearchProgress) -> EvidencePack:
        planner = ResearchPlanner(
            model=plan_model,
            retriever=SessionScopedSearch(sessions, embed=embed),
            sources=await live.get(sessions),
        )
        return await planner.research(request, progress=progress)

    return AnswerPipeline(
        resolve=resolve,
        research=research,
        compose=ModelComposer(model=compose_model).compose,
        store=SqlAnswerStore(sessions, embed=embed),
    )
