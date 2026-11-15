import asyncio
import json

from app.core.db import dispose_engine, session_scope
from app.services.craft_seed import seed_crafts


async def run() -> dict[str, int]:
    async with session_scope() as session:
        counts = await seed_crafts(session)
    await dispose_engine()
    return counts


def main() -> int:
    print(json.dumps(asyncio.run(run())))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
