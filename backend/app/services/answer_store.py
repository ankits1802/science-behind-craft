from __future__ import annotations

import uuid
from collections.abc import Iterable, Sequence

from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.composer.composer import ModelComposer
from app.composer.translation import ModelTranslator
from app.core.errors import InvalidInput
from app.core.shielded import ShieldedWork
from app.models import Answer
from app.planner.orchestrator import ResearchPlanner
from app.planner.understanding import ModelUnderstander
from app.research.blocks import ImagesBlock
from app.research.composition import ComposedAnswer
from app.research.crafts import CraftQuery, CraftRef, CraftResolution
from app.research.depth import depth_policy
from app.research.embedding import TextEmbedder
from app.research.evidence_pack import EvidencePack, ResearchTrail
from app.research.explainer import Explainer
from app.research.planning import PlanRequest
from app.research.sections import AnswerPlans
from app.research.stream import ResearchProgress
from app.research.structured import StructuredModel
from app.research.term_marking import GlossaryEntry
from app.research.understanding import Understanding
from app.retrieval.hybrid import SessionScopedSearch
from app.science.records import ProcessRecords

from . import knowledge_view
from .answer_events import CitedClaims, cited_claims
from .answer_sections import ClaimsOf
from .answer_translation import AnswerTranslation
from .answering import AnswerAsk, AnswerPipeline
from .craft_process import process_records
from .craft_resolver import CraftIndexStore, DatabaseCraftResolver
from .live_sources import LiveSourcesStore
from .piece_store import SqlPieceStore
from .research_write_back import sentence_claim_ids, store_live_research
from .section_enrichment import EnrichmentTools
from .section_images import SectionImagesAsk, section_images
from .term_glossary import glossary_entries
from .translation_cache import SqlTranslationCache

__all__ = [
    "EXPLAINER_PAYLOAD_KEY",
    "SqlAnswerStore",
    "build_answer_enrichment",
    "build_answer_pipeline",
    "build_answer_translation",
]

EXPLAINER_PAYLOAD_KEY = "explainer"


class SqlAnswerStore:
    def __init__(
        self, sessions: async_sessionmaker[AsyncSession], *, embed: TextEmbedder, shield: ShieldedWork
    ) -> None:
        self._sessions = sessions
        self._embed = embed
        self._shield = shield

    async def stored_claims(self, craft_slug: str, question: str, mode: str) -> CitedClaims:
        async with self._sessions() as session:
            craft = await knowledge_view.resolve_craft(session, craft_slug)
            if craft is None:
                raise InvalidInput(f"No craft has the slug {craft_slug!r}")
            views, sources = await knowledge_view.claims_for(session, craft, mode=mode, question=question)
        return cited_claims(views, sources)

    async def begin(self, ask: AnswerAsk, understanding: Understanding) -> uuid.UUID:
        return await self._shield.run(self._begun(ask, understanding), name="answer record")

    async def keep(self, answer_id: uuid.UUID, pack: EvidencePack, composed: ComposedAnswer) -> ClaimsOf:
        return await self._shield.run(self._kept(answer_id, pack, composed), name="answer write-back")

    async def finish(
        self,
        answer_id: uuid.UUID,
        *,
        plans: AnswerPlans,
        claim_ids: Sequence[uuid.UUID],
        explainer: Explainer | None,
    ) -> None:
        await self._shield.run(self._finished(answer_id, plans, claim_ids, explainer), name="answer record")

    async def process(self, craft_slug: str) -> ProcessRecords | None:
        async with self._sessions() as session:
            craft = await knowledge_view.resolve_craft(session, craft_slug)
            return await process_records(session, craft) if craft is not None else None

    async def _begun(self, ask: AnswerAsk, understanding: Understanding) -> uuid.UUID:
        answer_id = uuid.uuid4()
        async with self._sessions() as session:
            craft = understanding.craft
            row = await knowledge_view.resolve_craft(session, craft.slug) if craft else None
            session.add(
                Answer(
                    id=answer_id,
                    userId=ask.user_id,
                    question=ask.question,
                    language=understanding.language,
                    mode=depth_policy(understanding.depth).mode,
                    craftId=row.id if row else None,
                    understanding=understanding.model_dump(mode="json", by_alias=True),
                )
            )
            await session.commit()
        return answer_id

    async def _kept(self, answer_id: uuid.UUID, pack: EvidencePack, composed: ComposedAnswer) -> ClaimsOf:
        async with self._sessions() as session:
            stored = None
            if pack.documents:
                stored = await store_live_research(
                    session, pack, composed, embed=self._embed, found_by="ANSWER", answer_id=answer_id
                )
            await session.commit()
        return sentence_claim_ids(composed, stored)

    async def _finished(
        self,
        answer_id: uuid.UUID,
        plans: AnswerPlans,
        claim_ids: Sequence[uuid.UUID],
        explainer: Explainer | None,
    ) -> None:
        tiers = dict.fromkeys(tier for section in plans.sections for tier in section.plan.tiers)
        values = {
            "plan": plans.model_dump(mode="json", by_alias=True),
            "claimIds": list(claim_ids),
            "tiersUsed": list(tiers),
        }
        if plans.sections:
            values["mode"] = plans.sections[0].plan.mode
        if explainer is not None:
            values["payload"] = {EXPLAINER_PAYLOAD_KEY: explainer.model_dump(mode="json", by_alias=True)}
        async with self._sessions() as session:
            await session.execute(update(Answer).where(Answer.id == answer_id).values(**values))
            await session.commit()

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
    translate_model: StructuredModel,
    embed: TextEmbedder,
    shield: ShieldedWork,
) -> AnswerPipeline:
    async def resolve(query: CraftQuery) -> CraftResolution:
        async with sessions() as session:
            return await DatabaseCraftResolver(session, store=index, embed=embed).resolve(query)

    understander = ModelUnderstander(model=plan_model, resolve=resolve)

    async def research(
        request: PlanRequest, progress: ResearchProgress, trail: ResearchTrail
    ) -> EvidencePack:
        planner = ResearchPlanner(
            model=plan_model,
            retriever=SessionScopedSearch(sessions, embed=embed),
            sources=await live.get(sessions),
        )
        return await planner.research(request, progress=progress, trail=trail)

    return AnswerPipeline(
        understand=understander.understand,
        research=research,
        compose=ModelComposer(model=compose_model).compose,
        store=SqlAnswerStore(sessions, embed=embed, shield=shield),
        translation=build_answer_translation(sessions, model=translate_model),
        pieces=SqlPieceStore(sessions, embed=embed, shield=shield),
        enrichment=build_answer_enrichment(sessions, live),
    )


def build_answer_enrichment(
    sessions: async_sessionmaker[AsyncSession], live: LiveSourcesStore
) -> EnrichmentTools:
    async def glossary(craft: CraftRef) -> list[GlossaryEntry]:
        async with sessions() as session:
            found = await knowledge_view.resolve_craft(session, craft.slug)
            return await glossary_entries(session, [found.id] if found is not None else [])

    async def pictures(ask: SectionImagesAsk) -> ImagesBlock | None:
        return await (await section_images(sessions, live)).block(ask)

    return EnrichmentTools(glossary=glossary, pictures=pictures)


def build_answer_translation(
    sessions: async_sessionmaker[AsyncSession], *, model: StructuredModel
) -> AnswerTranslation:
    return AnswerTranslation(translator=ModelTranslator(model=model), cache=SqlTranslationCache(sessions))
