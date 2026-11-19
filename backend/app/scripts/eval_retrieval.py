import asyncio
import json
from typing import Any

from app.core.db import dispose_engine, session_scope, sessionmaker
from app.core.errors import AppError
from app.providers.embedding import router_embedder
from app.retrieval.evaluation import evaluate_golden, visible_claims
from app.retrieval.golden import GOLDEN_QUESTIONS
from app.retrieval.hybrid import SessionScopedSearch
from app.services.claim_seed import seed_id


async def run() -> dict[str, Any]:
    ids = {key: seed_id("claim", key) for question in GOLDEN_QUESTIONS for key in question.expected}
    try:
        async with session_scope() as session:
            present = await visible_claims(session, ids.values())
        retriever = SessionScopedSearch(sessionmaker(), embed=router_embedder())
        report = await evaluate_golden(retriever, GOLDEN_QUESTIONS, claim_id=ids.__getitem__, present=present)
    except AppError as error:
        return {"ok": False, "error": str(error)}
    finally:
        await dispose_engine()
    return {"ok": True, **report.as_dict()}


def main() -> int:
    report = asyncio.run(run())
    print(json.dumps(report))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
