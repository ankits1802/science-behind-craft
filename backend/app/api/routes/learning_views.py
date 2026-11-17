import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.deps import get_current_user
from app.core.http_cache import PRIVATE_NO_CACHE
from app.models import Answer, Craft, User
from app.models.enums import DISCIPLINES
from app.research.blocks_learning import COMPARE_CRAFTS_MAX, COMPARE_CRAFTS_MIN
from app.research.crafts import SLUG_MAX_CHARS
from app.research.quiz import explainer_quiz
from app.research.subject_keys import TERM_KEY, TERM_KEY_MAX_CHARS
from app.research.vocabulary import Discipline
from app.services import knowledge_view
from app.services.answering import NOT_FOUND_DETAIL
from app.services.craft_compare import craft_comparison
from app.services.explainer_payload import stored_explainer
from app.services.shared_concepts import craft_shared_science, shared_concept_of
from app.services.simulation_hiding import with_hidden_marks
from app.services.visible_claims import visible_claim_ids

router = APIRouter(tags=["learning"])

CRAFTS_DETAIL = f"Choose {COMPARE_CRAFTS_MIN} to {COMPARE_CRAFTS_MAX} different crafts."
SECTIONS_DETAIL = "Choose sections of this explainer, each once."

Slugs = Annotated[list[str], Query(min_length=1)]
Facets = Annotated[list[Discipline] | None, Query()]
SectionIds = Annotated[list[str] | None, Query()]


@router.get("/crafts/{slug}/shared-science")
async def get_craft_shared_science(
    slug: str,
    response: Response,
    _: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> Any:
    body = await craft_shared_science(session, await _known_craft(session, slug))
    response.headers["Cache-Control"] = PRIVATE_NO_CACHE
    return body.model_dump(mode="json", by_alias=True)


@router.get("/shared-science/{term_key}")
async def get_shared_concept(
    response: Response,
    term_key: str = Path(max_length=TERM_KEY_MAX_CHARS, pattern=TERM_KEY.pattern),
    craft: str | None = Query(default=None, min_length=1, max_length=SLUG_MAX_CHARS),
    _: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> Any:
    focus = await _known_craft(session, craft) if craft is not None else None
    body = await shared_concept_of(session, term_key, focus)
    if body is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, NOT_FOUND_DETAIL)
    response.headers["Cache-Control"] = PRIVATE_NO_CACHE
    return body.model_dump(mode="json", by_alias=True)


@router.get("/compare")
async def get_comparison(
    response: Response,
    crafts: Slugs,
    facets: Facets = None,
    _: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> Any:
    if not COMPARE_CRAFTS_MIN <= len(crafts) <= COMPARE_CRAFTS_MAX or any(
        len(s) > SLUG_MAX_CHARS for s in crafts
    ):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, CRAFTS_DETAIL)
    rows = [await _known_craft(session, slug) for slug in crafts]
    if len({row.id for row in rows}) != len(rows):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, CRAFTS_DETAIL)
    body = await craft_comparison(session, rows, list(dict.fromkeys(facets or DISCIPLINES)))
    if body is None:
        return Response(status_code=status.HTTP_204_NO_CONTENT, headers={"Cache-Control": PRIVATE_NO_CACHE})
    response.headers["Cache-Control"] = PRIVATE_NO_CACHE
    return body.model_dump(mode="json", by_alias=True)


@router.get("/answers/{answer_id}/quiz")
async def get_answer_quiz(
    answer_id: uuid.UUID,
    response: Response,
    sections: SectionIds = None,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> Any:
    payload = await session.scalar(
        select(Answer.payload).where(Answer.id == answer_id, Answer.userId == user.id)
    )
    explainer = stored_explainer(answer_id, payload)
    if explainer is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, NOT_FOUND_DETAIL)
    chosen = list(sections or [])
    if len(set(chosen)) != len(chosen) or not set(chosen) <= {section.id for section in explainer.sections}:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, SECTIONS_DETAIL)
    shown = await with_hidden_marks(session, explainer)
    visible = await visible_claim_ids(session, shown)
    quiz = explainer_quiz(shown, visible_claim_ids=visible, section_ids=chosen)
    if quiz is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, NOT_FOUND_DETAIL)
    response.headers["Cache-Control"] = PRIVATE_NO_CACHE
    return quiz.model_dump(mode="json", by_alias=True)


async def _known_craft(session: AsyncSession, slug: str) -> Craft:
    craft = await knowledge_view.resolve_craft(session, slug)
    if craft is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, NOT_FOUND_DETAIL)
    return craft
