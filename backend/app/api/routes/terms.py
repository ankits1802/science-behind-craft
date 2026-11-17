from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Path, Request, status

from app.core.db import sessionmaker
from app.core.deps import get_current_user
from app.core.errors import Refused
from app.core.rate_limit import term_attempt
from app.core.roles import is_uncapped
from app.models import User
from app.providers.router import Principal
from app.providers.structured import router_structured_model
from app.research.subject_keys import TERM_KEY_MAX_CHARS
from app.research.vocabulary import CANONICAL_LANGUAGE, AnswerLanguage
from app.services.ai_providers import AiTask
from app.services.term_summaries import TermLookup
from app.services.term_wiring import build_term_lookup

router = APIRouter(tags=["terms"])

THROTTLED_DETAIL = "You have opened a lot of terms in the last few minutes. Wait a little and try again."


async def term_lookup(request: Request, user: User = Depends(get_current_user)) -> TermLookup:
    principal = Principal(user_id=user.id, role=user.role)
    return await build_term_lookup(
        sessions=sessionmaker(),
        live=request.app.state.live_sources,
        summarise_model=router_structured_model(AiTask.SUMMARISE, principal),
        translate_model=router_structured_model(AiTask.TRANSLATE, principal),
    )


def throttle(user: User = Depends(get_current_user)) -> None:
    if is_uncapped(user):
        return
    allowed, retry = term_attempt(str(user.id))
    if not allowed:
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            THROTTLED_DETAIL,
            {"Retry-After": str(max(1, int(retry + 0.999)))},
        )


@router.get("/terms/{key}", dependencies=[Depends(throttle)])
async def term_summary(
    key: str = Path(min_length=1, max_length=TERM_KEY_MAX_CHARS),
    language: AnswerLanguage = CANONICAL_LANGUAGE,
    lookup: TermLookup = Depends(term_lookup),
) -> dict[str, Any]:
    try:
        summary = await lookup.summary(key, language)
    except Refused as refusal:
        raise HTTPException(status.HTTP_404_NOT_FOUND, refusal.message) from None
    return summary.model_dump(mode="json", by_alias=True)
