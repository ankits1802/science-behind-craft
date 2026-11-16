import hashlib
import logging
from datetime import UTC, datetime
from functools import lru_cache
from pathlib import Path
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from pydantic import Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.voice_deps import current_voice, voice_runtime, voice_store
from app.core.config import get_settings
from app.core.db import get_session, sessionmaker
from app.core.deps import get_current_user, refusal_for
from app.core.errors import AppError
from app.core.rate_limit import ask_attempt
from app.core.roles import Capability, can
from app.models import User
from app.providers.embedding import router_embedder
from app.providers.router import Principal
from app.providers.structured import router_structured_model
from app.research.stream import event_stream
from app.research.vocabulary import ANSWER_LANGUAGES, AnswerLanguage, language_option
from app.schemas.common import APIModel
from app.services import knowledge_view
from app.services.ai_providers import AiTask
from app.services.answer_store import build_answer_pipeline
from app.services.answering import NOT_FOUND_DETAIL, AnswerAsk, AnswerPipeline, answer_question
from app.voice.availability import HIDDEN_VOICE, voice_availability
from app.voice.runtime import VoiceRuntime, VoiceSettings
from app.voice.store import SqlVoiceStore

router = APIRouter(tags=["knowledge"])
logger = logging.getLogger(__name__)

NOTICE_PATH = Path(__file__).resolve().parents[2] / "data" / "privacy_notice.md"
NOTICE_VERSION = "2026-11-16"
NOTICE_PUBLISHED_AT = "2026-11-16T00:00:00+05:30"
NOTICE_TITLE = "Privacy notice"

ANSWER_MODES = ("VERIFIED", "HYBRID", "DEEP")
DEFAULT_ANSWER_MODE = "HYBRID"
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


async def offered_voice(
    user: User = Depends(get_current_user),
    store: SqlVoiceStore = Depends(voice_store),
    runtime: VoiceRuntime = Depends(voice_runtime),
    voice: VoiceSettings = Depends(current_voice),
) -> dict[str, Any]:
    try:
        return await voice_availability(
            user, store=store, runtime=runtime, voice=voice, now=datetime.now(UTC)
        )
    except AppError as error:
        logger.warning("voice availability could not be read, voice hidden: %s", error)
        return dict(HIDDEN_VOICE)


@router.get("/answers/config")
async def answers_config(
    user: User = Depends(get_current_user), voice: dict[str, Any] = Depends(offered_voice)
) -> dict[str, Any]:
    modes = [mode for mode in ANSWER_MODES if can(user, mode_capability(mode))]
    return {
        "modes": modes,
        "defaultMode": DEFAULT_ANSWER_MODE if DEFAULT_ANSWER_MODE in modes else next(iter(modes), None),
        "voice": voice,
        "languages": answer_languages(),
    }


class AskRequest(APIModel):
    question: str = Field(min_length=2, max_length=1000)
    mode: Literal["VERIFIED", "HYBRID", "DEEP"] = DEFAULT_ANSWER_MODE
    craftSlug: str | None = Field(default=None, max_length=200)
    language: AnswerLanguage | None = None
    conversationId: str | None = Field(default=None, max_length=64)


def answer_languages() -> list[dict[str, str]]:
    return [language_option(code) for code in ANSWER_LANGUAGES]


def mode_capability(mode: str) -> Capability:
    return Capability.ASK_DEEP if mode == "DEEP" else Capability.ASK_STANDARD


def withheld_terms(user: User) -> tuple[str, ...]:
    name = (user.name or "").strip()
    return (name,) if 2 <= len(name) <= 200 else ()


def answer_pipeline(request: Request, user: User = Depends(get_current_user)) -> AnswerPipeline:
    principal = Principal(user_id=user.id, role=user.role)
    return build_answer_pipeline(
        sessions=sessionmaker(),
        index=request.app.state.craft_index,
        live=request.app.state.live_sources,
        plan_model=router_structured_model(AiTask.PLAN, principal),
        compose_model=router_structured_model(AiTask.COMPOSE, principal),
        translate_model=router_structured_model(AiTask.TRANSLATE, principal),
        embed=router_embedder(principal),
        shield=request.app.state.shielded_work,
    )


@router.post("/answers/stream")
async def answers_stream(
    payload: AskRequest,
    user: User = Depends(get_current_user),
    pipeline: AnswerPipeline = Depends(answer_pipeline),
) -> StreamingResponse:
    capability = mode_capability(payload.mode)
    if not can(user, capability):
        raise HTTPException(status.HTTP_403_FORBIDDEN, refusal_for(capability))
    allowed, retry = ask_attempt(str(user.id))
    if not allowed:
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            THROTTLED_DETAIL,
            {"Retry-After": str(max(1, int(retry + 0.999)))},
        )
    ask = AnswerAsk(
        question=payload.question,
        mode=payload.mode,
        craft_slug=payload.craftSlug,
        language=payload.language,
        user_id=user.id,
        withheld_terms=withheld_terms(user),
    )
    return StreamingResponse(
        event_stream(lambda emit: answer_question(ask, pipeline, emit)),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-store", "X-Accel-Buffering": "no"},
    )
