import asyncio
import json
from typing import Any

from app.core.config import get_settings
from app.core.db import dispose_engine, session_scope
from app.providers.embedding import router_embedder
from app.services.field_voices_run import run_field_voices


async def run() -> dict[str, Any]:
    try:
        report = await run_field_voices(get_settings(), open_session=session_scope, embed=router_embedder())
    finally:
        await dispose_engine()
    return report.as_dict()


def main() -> int:
    report = asyncio.run(run())
    print(json.dumps(report))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
