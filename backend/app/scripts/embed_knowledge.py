import argparse
import asyncio
import json
from dataclasses import asdict
from typing import Any

from sqlalchemy import select

from app.core.db import dispose_engine, session_scope
from app.core.errors import AppError
from app.providers.embedding import router_embedder
from app.retrieval.deadline import Deadline
from app.retrieval.indexing import embed_pending
from app.retrieval.stamps import current_embedding_model


async def run(seconds: float | None) -> dict[str, Any]:
    deadline = Deadline.after(seconds) if seconds is not None else None
    try:
        async with session_scope() as session:
            counts = await embed_pending(session, router_embedder(), deadline=deadline)
            model = await session.scalar(select(current_embedding_model()))
    except AppError as error:
        return {"ok": False, "error": str(error)}
    finally:
        await dispose_engine()
    return {"ok": True, "model": model, **asdict(counts)}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="embed_knowledge")
    parser.add_argument(
        "--seconds", type=float, help="stop starting new batches after this many seconds; the rest waits"
    )
    args = parser.parse_args(argv)
    report = asyncio.run(run(args.seconds))
    print(json.dumps(report))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
