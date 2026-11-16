import asyncio
import json
from datetime import UTC, datetime
from typing import Any

from app.core.config import get_settings
from app.core.db import dispose_engine, session_scope
from app.services.portal_craft_sync import run_sync


async def run() -> dict[str, Any]:
    try:
        report = await run_sync(
            get_settings(),
            open_session=session_scope,
            synced_at=datetime.now(UTC).isoformat(timespec="seconds"),
        )
    finally:
        await dispose_engine()
    return report.as_dict()


def main() -> int:
    report = asyncio.run(run())
    print(json.dumps(report))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
