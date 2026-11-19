import asyncio
import json
from dataclasses import asdict

from app.core.db import dispose_engine, session_scope
from app.services.page_layouts_backfill import backfill_page_layouts


async def run() -> dict[str, list[str]]:
    try:
        async with session_scope() as session:
            report = await backfill_page_layouts(session)
    finally:
        await dispose_engine()
    return asdict(report)


def main() -> int:
    print(json.dumps(asyncio.run(run())))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
