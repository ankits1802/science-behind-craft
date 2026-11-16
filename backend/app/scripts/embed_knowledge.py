import asyncio
import json
from dataclasses import asdict

from app.core.db import dispose_engine, session_scope
from app.providers.embedding import router_embedder
from app.retrieval.indexing import embed_pending


async def run() -> dict[str, int]:
    async with session_scope() as session:
        counts = await embed_pending(session, router_embedder())
    await dispose_engine()
    return asdict(counts)


def main() -> int:
    print(json.dumps(asyncio.run(run())))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
