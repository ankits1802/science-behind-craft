import argparse
import asyncio
import json
from typing import Any

import httpx

from app.core.config import get_settings
from app.core.db import dispose_engine, session_scope
from app.providers.elevenlabs import ElevenLabs
from app.voice.agent import (
    CLIENT_TOOLS,
    LLM_SECRET_NAME,
    AgentPlan,
    agent_body,
    artisan_agent_body,
    provision_agent,
    provision_artisan_agent,
)
from app.voice.languages import VOICE_LANGUAGES
from app.voice.runtime import BEARER_MIN_CHARS, voice_settings


async def run(*, api_base_url: str | None, dry_run: bool, artisan: bool = False) -> dict[str, Any]:
    settings = get_settings()
    try:
        async with session_scope() as session:
            voice = await voice_settings(session, settings)
    finally:
        await dispose_engine()
    if len(voice.llm_bearer or "") < BEARER_MIN_CHARS:
        raise SystemExit(f"VOICE_LLM_BEARER must be at least {BEARER_MIN_CHARS} characters")
    plan = AgentPlan(
        api_base_url=api_base_url or settings.public_api_url or "",
        llm_bearer=voice.llm_bearer or "",
        voice_id=voice.voice_id,
        max_live_sessions=voice.max_live_sessions,
        agent_id=(settings.elevenlabs_artisan_agent_id or "").strip() or None if artisan else voice.agent_id,
    )
    if artisan:
        return await _artisan(plan, voice.api_key, dry_run=dry_run)
    if dry_run:
        return {"agent": agent_body(plan, secret_id=f"<{LLM_SECRET_NAME}>", tool_ids=list(CLIENT_TOOLS))}
    if not voice.api_key:
        raise SystemExit("ELEVENLABS_API_KEY is not set")
    async with httpx.AsyncClient(follow_redirects=False) as client:
        done = await provision_agent(ElevenLabs(api_key=voice.api_key, client=client), plan)
    return {
        "agentId": done.agent_id,
        "created": done.created,
        "toolIds": done.tool_ids,
        "secret": LLM_SECRET_NAME,
        "languages": list(VOICE_LANGUAGES),
    }


async def _artisan(plan: AgentPlan, api_key: str | None, *, dry_run: bool) -> dict[str, Any]:
    if dry_run:
        return {"agent": artisan_agent_body(plan, secret_id=f"<{LLM_SECRET_NAME}>")}
    if not api_key:
        raise SystemExit("ELEVENLABS_API_KEY is not set")
    async with httpx.AsyncClient(follow_redirects=False) as client:
        done = await provision_artisan_agent(ElevenLabs(api_key=api_key, client=client), plan)
    return {"agentId": done.agent_id, "created": done.created, "setting": "ELEVENLABS_ARTISAN_AGENT_ID"}


def main() -> int:
    parser = argparse.ArgumentParser(description="Create or update the KalaVigyan ElevenLabs voice agent.")
    parser.add_argument("--api-base-url", help="https origin ElevenLabs calls (defaults to PUBLIC_API_URL)")
    parser.add_argument("--dry-run", action="store_true", help="print the agent body and change nothing")
    parser.add_argument("--artisan", action="store_true", help="the artisan conversations agent instead")
    args = parser.parse_args()
    done = asyncio.run(run(api_base_url=args.api_base_url, dry_run=args.dry_run, artisan=args.artisan))
    print(json.dumps(done, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
