import hashlib
import json
from collections.abc import AsyncIterator
from functools import lru_cache
from pathlib import Path
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.db import get_session
from app.core.deps import get_current_user
from app.core.rate_limit import ask_attempt
from app.models import Craft, User
from app.schemas.common import APIModel
from app.services import knowledge_view

router = APIRouter(tags=["knowledge"])

NOTICE_PATH = Path(__file__).resolve().parents[2] / "data" / "privacy_notice.md"
NOTICE_VERSION = "2026-11-16"
NOTICE_PUBLISHED_AT = "2026-11-16T00:00:00+05:30"
NOTICE_TITLE = "Privacy notice"

ANSWER_MODES = ("VERIFIED",)
ANSWER_LIMIT = 14
OPEN_QUESTION_LIMIT = 4
CANDIDATE_LIMIT = 5
NOT_FOUND_DETAIL = "No craft has that address."
NO_EVIDENCE_DETAIL = (
    "The evidence base has no cited finding for this yet. Try naming the craft, a material or a step."
)
THROTTLED_DETAIL = "You have asked a lot in the last few minutes. Wait a little and ask again."


@lru_cache
def privacy_notice_text() -> str:
    return NOTICE_PATH.read_text(encoding="utf-8")


def notice_sha256() -> str:
    return hashlib.sha256(privacy_notice_text().encode("utf-8")).hexdigest()


@router.get("/privacy/notice")
async def privacy_notice() -> dict[str, Any]:
    settings = get_settings()
    address = (settings.mail_reply_to or "").strip()
    contact = f", or write to {address}" if address else ""
    return {
        "version": NOTICE_VERSION,
        "title": NOTICE_TITLE,
        "body": privacy_notice_text().replace("{contact}", contact),
        "publishedAt": NOTICE_PUBLISHED_AT,
    }


@router.get("/crafts/{slug}/profile")
async def craft_profile(
    slug: str, _: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)
) -> dict[str, Any]:
    craft = await knowledge_view.resolve_craft(session, slug)
    if craft is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, NOT_FOUND_DETAIL)
    return await knowledge_view.craft_profile(session, craft)


@router.get("/map/crafts")
async def map_crafts(
    _: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)
) -> list[dict[str, Any]]:
    return await knowledge_view.map_points(session)


@router.get("/answers/config")
async def answers_config(_: User = Depends(get_current_user)) -> dict[str, Any]:
    return {
        "modes": list(ANSWER_MODES),
        "defaultMode": ANSWER_MODES[0],
        "voice": {"configured": False, "languages": []},
        "languages": [{"code": "en", "label": "English"}],
    }


class AskRequest(APIModel):
    question: str = Field(min_length=2, max_length=1000)
    mode: Literal["VERIFIED", "HYBRID", "DEEP"] = "VERIFIED"
    craftSlug: str | None = Field(default=None, max_length=200)
    language: str | None = Field(default=None, max_length=16)
    conversationId: str | None = Field(default=None, max_length=64)


def sse(event: str, data: Any) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False, separators=(',', ':'))}\n\n"


def follow_ups(craft_name: str, headings: list[str]) -> list[str]:
    prompts = {
        "Materials and tools": f"Which materials does {craft_name} depend on, and why?",
        "Process": f"What happens at each step of {craft_name}?",
        "How it works": f"What is the chemistry or physics behind {craft_name}?",
        "Place and climate": f"How do local water, soil and climate shape {craft_name}?",
        "The artisan's judgement": f"How do artisans judge when a step of {craft_name} is done?",
        "History": f"Where did {craft_name} come from?",
    }
    return [prompts[h] for h in prompts if h not in headings][:3]


async def _answer_events(session: AsyncSession, payload: AskRequest) -> AsyncIterator[str]:
    craft: Craft | None = None
    if payload.craftSlug:
        craft = await knowledge_view.resolve_craft(session, payload.craftSlug)
        if craft is None:
            yield sse("error", {"message": NOT_FOUND_DETAIL})
            yield sse("done", {"answerId": None})
            return
    else:
        matches = knowledge_view.match_aliases(payload.question, await knowledge_view.alias_rows(session))
        if len(matches) > 1:
            rows = (
                (await session.execute(select(Craft).where(Craft.id.in_(matches)).order_by(Craft.name)))
                .scalars()
                .all()
            )
            yield sse(
                "match",
                {
                    "status": "AMBIGUOUS",
                    "candidates": [knowledge_view.craft_ref(c) for c in rows[:CANDIDATE_LIMIT]],
                },
            )
            yield sse("done", {"answerId": None})
            return
        if matches:
            craft = await session.get(Craft, matches[0])
    if craft is None:
        yield sse("match", {"status": "NONE"})
        yield sse(
            "error", {"message": "Name the craft you are asking about, or open it from the craft list."}
        )
        yield sse("done", {"answerId": None})
        return
    yield sse("match", {"status": "RESOLVED", "craft": knowledge_view.craft_ref(craft)})
    concepts = await knowledge_view.craft_concepts(session, craft)
    claims, sources = await knowledge_view.claims_for(session, concepts, question=payload.question)
    ranked = sorted(claims, key=lambda c: (-c.rank, knowledge_view.LEVEL_ORDER.get(c.level, 9)))
    findings = [c for c in ranked if c.level != "HYPOTHESIS"][:ANSWER_LIMIT]
    open_questions = [c for c in ranked if c.level == "HYPOTHESIS"][:OPEN_QUESTION_LIMIT]
    if not findings and not open_questions:
        yield sse("error", {"message": NO_EVIDENCE_DETAIL})
        yield sse("done", {"answerId": None})
        return
    sent_sources: set[str] = set()
    sections: dict[str, str] = {}
    for view in knowledge_view.order_claims(findings):
        heading = knowledge_view.section_heading(view.concept_type)
        for cite in view.citations:
            if cite["sourceId"] not in sent_sources:
                sent_sources.add(cite["sourceId"])
                source = next(s for s in sources.values() if str(s.id) == cite["sourceId"])
                yield sse("source", knowledge_view.source_ref(source))
        if heading not in sections:
            sections[heading] = f"s{len(sections) + 1}"
            yield sse("section", {"id": sections[heading], "heading": heading})
        yield sse("sentence", {"sectionId": sections[heading], "sentence": view.payload()})
    for view in open_questions:
        for cite in view.citations:
            if cite["sourceId"] not in sent_sources:
                sent_sources.add(cite["sourceId"])
                source = next(s for s in sources.values() if str(s.id) == cite["sourceId"])
                yield sse("source", knowledge_view.source_ref(source))
        yield sse(
            "open_question",
            {"sectionId": "open", "heading": "Open questions", "sentence": view.payload()},
        )
    yield sse("follow_ups", {"items": follow_ups(craft.name, list(sections))})
    yield sse("done", {"answerId": None})


@router.post("/answers/stream")
async def answers_stream(
    payload: AskRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> StreamingResponse:
    if payload.mode not in ANSWER_MODES:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Choose Verified only.")
    allowed, retry = ask_attempt(str(user.id))
    if not allowed:
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            THROTTLED_DETAIL,
            {"Retry-After": str(max(1, int(retry + 0.999)))},
        )
    events = [event async for event in _answer_events(session, payload)]

    async def body() -> AsyncIterator[str]:
        for event in events:
            yield event

    return StreamingResponse(
        body(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-store", "X-Accel-Buffering": "no"},
    )
