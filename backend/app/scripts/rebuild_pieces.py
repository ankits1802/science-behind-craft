import asyncio
import json
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.db import dispose_engine, sessionmaker
from app.core.shielded import ShieldedWork
from app.providers import budget
from app.providers.answer_routes import answer_models
from app.providers.budget import AnswerSpend
from app.providers.embedding import router_embedder
from app.providers.router import Principal
from app.scripts.enrich_coverage import spent_since
from app.services.answer_store import build_answer_pipeline
from app.services.answering import AnswerPipeline
from app.services.coverage_enrichment import ENRICHMENT_DAILY_BUDGET_USD, ENRICHMENT_TAG
from app.services.craft_resolver import CraftIndexStore
from app.services.live_sources import LiveSourcesStore
from app.services.piece_rebuild import StaleGroup, rebuild_group, run_piece_rebuild, stale_groups


def rebuild_pipeline(
    depth: str,
    *,
    sessions: async_sessionmaker[AsyncSession],
    index: CraftIndexStore,
    live: LiveSourcesStore,
    shield: ShieldedWork,
) -> AnswerPipeline:
    spend = AnswerSpend(depth=depth)
    principal = Principal(answer=spend)
    optional = Principal(answer=spend.headroom())
    return build_answer_pipeline(
        sessions=sessions,
        index=index,
        live=live,
        models=answer_models(depth, principal=principal, optional=optional),
        embed=router_embedder(principal),
        shield=shield,
    )


async def run() -> dict[str, Any]:
    day_started_at = budget.day_start()
    sessions = sessionmaker()
    live = LiveSourcesStore()
    shield = ShieldedWork()
    index = CraftIndexStore()

    async def rebuild(group: StaleGroup) -> str:
        pipeline = rebuild_pipeline(group.depth, sessions=sessions, index=index, live=live, shield=shield)
        return await rebuild_group(group, pipeline)

    async def remaining() -> Decimal:
        return ENRICHMENT_DAILY_BUDGET_USD - await spent_since(ENRICHMENT_TAG, day_started_at)

    try:
        async with sessions() as session:
            groups = await stale_groups(session, now=datetime.now(UTC))
        report = await run_piece_rebuild(
            groups, rebuild=rebuild, remaining=remaining, budget_usd=ENRICHMENT_DAILY_BUDGET_USD
        )
        await shield.drain()
    finally:
        await live.aclose()
        await dispose_engine()
    return report.as_dict()


def main() -> int:
    report = asyncio.run(run())
    print(json.dumps(report))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
