import asyncio
import json
from dataclasses import asdict
from datetime import UTC, datetime
from typing import Any

import httpx

from app.core.config import get_settings
from app.core.db import dispose_engine, session_scope, sessionmaker
from app.providers.elevenlabs import ElevenLabs
from app.voice.runtime import voice_settings
from app.voice.store import SqlVoiceStore
from app.voice.upkeep import run_upkeep


async def run() -> dict[str, Any]:
    try:
        async with session_scope() as session:
            voice = await voice_settings(session, get_settings())
        async with httpx.AsyncClient(follow_redirects=False) as client:
            elevenlabs = ElevenLabs(api_key=voice.api_key, client=client) if voice.api_key else None
            report = await run_upkeep(SqlVoiceStore(sessionmaker()), elevenlabs, now=datetime.now(UTC))
    finally:
        await dispose_engine()
    return {**asdict(report), "reconciling": elevenlabs is not None, "ok": not report.failures}


def main() -> int:
    report = asyncio.run(run())
    print(json.dumps(report))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
