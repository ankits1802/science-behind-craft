import asyncio
import json
from datetime import UTC, datetime
from typing import Any

from app.core.db import dispose_engine, sessionmaker
from app.services.saved_recheck import recheck_saved


async def run() -> dict[str, Any]:
    try:
        report = await recheck_saved(sessionmaker(), now=datetime.now(UTC))
    finally:
        await dispose_engine()
    return report.as_dict()


def main() -> int:
    report = asyncio.run(run())
    print(json.dumps(report))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
