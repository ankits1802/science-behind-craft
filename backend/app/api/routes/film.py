from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.api.film_deps import UNAVAILABLE_DETAIL, FilmTools, film_store, film_tools
from app.api.listen_deps import throttled_voice_user
from app.core.errors import AppError
from app.core.rate_limit import film_score_attempt
from app.core.shielded import ShieldedWork
from app.models import User
from app.providers.router import Principal
from app.research.vocabulary import AnswerLanguage
from app.voice.film_score import NOTHING_MESSAGE, ScoreAsk, ScoreDeps, ScoreRefused, film_score
from app.voice.film_store import SqlFilmStore

router = APIRouter(prefix="/answers", tags=["film"])
logger = logging.getLogger(__name__)

THROTTLED_DETAIL = "You have asked for film music many times in a few minutes. Wait a little and try again."

throttle = throttled_voice_user(film_score_attempt, THROTTLED_DETAIL)


def utc_now() -> datetime:
    return datetime.now(UTC)


@router.get("/{answer_id}/film-score")
async def film_score_of(
    answer_id: uuid.UUID,
    language: AnswerLanguage,
    request: Request,
    *,
    user: User = Depends(throttle),
    store: SqlFilmStore = Depends(film_store),
    tools: FilmTools = Depends(film_tools),
) -> dict[str, Any]:
    explainer = await store.explainer(answer_id, user.id)
    if explainer is None or explainer.understood.language != language:
        raise HTTPException(status.HTTP_404_NOT_FOUND, NOTHING_MESSAGE)
    ask = ScoreAsk(principal=Principal(user_id=user.id, role=user.role), explainer=explainer)
    deps = ScoreDeps(objects=tools.objects, maker=tools.maker, clock=utc_now)
    shield: ShieldedWork = request.app.state.shielded_work
    try:
        score = await shield.run(film_score(ask, deps), name=f"film score of answer {answer_id}")
    except ScoreRefused as error:
        raise HTTPException(status.HTTP_404_NOT_FOUND, error.message) from None
    except AppError as error:
        logger.warning("the film score of answer %s failed: %s", answer_id, error)
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, UNAVAILABLE_DETAIL) from None
    return score.model_dump(mode="json", by_alias=True)
