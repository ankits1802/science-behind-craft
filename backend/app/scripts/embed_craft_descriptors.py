import asyncio
import json

from app.core.db import dispose_engine, session_scope
from app.providers.embedding import router_embedder
from app.services.craft_resolver import fill_descriptor_embeddings


async def run() -> dict[str, int]:
    async with session_scope() as session:
        filled = await fill_descriptor_embeddings(session, router_embedder())
    await dispose_engine()
    return {"filled": filled}


def main() -> int:
    print(json.dumps(asyncio.run(run())))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
