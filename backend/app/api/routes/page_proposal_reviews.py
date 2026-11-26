from __future__ import annotations

import uuid
from collections.abc import Awaitable
from datetime import UTC, datetime
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Path, Response, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.structure_proposal_deps import site_origin
from app.core.db import get_session
from app.core.deps import get_current_user
from app.core.errors import InvalidInput
from app.core.roles import Capability, can
from app.models import User
from app.models.page_proposals import DRAWN_SIDES
from app.providers.embedding import router_embedder
from app.providers.router import Principal
from app.research.page_proposal_review import (
    DrawAsk,
    PageDecisionBody,
    PageDecisionReply,
    PageDrawing,
    PageProposalList,
    PageProposalView,
)
from app.services.page_proposal_decisions import decide_page
from app.services.page_proposal_drawings import draw_side
from app.services.page_proposal_pictures import drawn_picture
from app.services.page_proposal_reviews import (
    open_page_proposals,
    page_proposal,
    proposal_document,
    reviewable,
)
from app.services.page_renders import page_renderer
from app.services.page_revalidation import refresh_pages
from app.services.review_queue_errors import DecisionConflict, NotYourQueue, OwnItem, UnknownItem
from app.services.written_vectors import embed_decided

router = APIRouter(prefix="/review-queue/pages", tags=["review"])

NOT_AN_ADMIN = "Page proposals are reviewed by Admins and Master Admins."
NO_PICTURE = "This page proposal keeps no picture by that name."
PRIVATE_HEADERS = {"Cache-Control": "private, no-store", "X-Robots-Tag": "noindex, nofollow"}
PICTURE_HEADERS = {"Cache-Control": "private, max-age=3600", "X-Content-Type-Options": "nosniff"}
PICTURE_MIME = "image/jpeg"
NAME_PATTERN = r"^[a-z0-9-]{1,80}$"

Side = Literal[*DRAWN_SIDES]


async def page_reviewer(user: User = Depends(get_current_user)) -> User:
    if not can(user, Capability.REVIEW_CONTRIBUTIONS):
        raise HTTPException(status.HTTP_403_FORBIDDEN, NOT_AN_ADMIN)
    return user


@router.get("")
async def page_proposals(
    user: User = Depends(page_reviewer), session: AsyncSession = Depends(get_session)
) -> PageProposalList:
    return await _read(open_page_proposals(session, user, site=site_origin(), now=_now()))


@router.get("/{proposal_id}")
async def one_page_proposal(
    proposal_id: uuid.UUID, user: User = Depends(page_reviewer), session: AsyncSession = Depends(get_session)
) -> PageProposalView:
    return await _read(page_proposal(session, user, proposal_id, site=site_origin()))


@router.get("/{proposal_id}/documents/{side}")
async def page_document(
    proposal_id: uuid.UUID,
    side: Side,
    user: User = Depends(page_reviewer),
    session: AsyncSession = Depends(get_session),
) -> JSONResponse:
    document = await _read(proposal_document(session, user, proposal_id, side))
    return JSONResponse(document, headers=PRIVATE_HEADERS)


@router.get("/{proposal_id}/pictures/{side}/{name}")
async def page_picture(
    proposal_id: uuid.UUID,
    side: Side,
    name: str = Path(pattern=NAME_PATTERN),
    user: User = Depends(page_reviewer),
    session: AsyncSession = Depends(get_session),
) -> Response:
    await _read(reviewable(session, user, proposal_id))
    found = await drawn_picture(session, proposal_id, side, name)
    if found is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, NO_PICTURE)
    return Response(found.data, media_type=PICTURE_MIME, headers=PICTURE_HEADERS)


@router.post("/{proposal_id}/draw")
async def draw_page(
    proposal_id: uuid.UUID,
    body: DrawAsk,
    user: User = Depends(page_reviewer),
    session: AsyncSession = Depends(get_session),
) -> PageDrawing:
    drawing = draw_side(
        session, user, proposal_id, body.side, renderer=page_renderer(), site=site_origin(), now=_now()
    )
    return await _changed(session, drawing)


@router.post("/{proposal_id}/decide")
async def decide_page_proposal(
    proposal_id: uuid.UUID,
    body: PageDecisionBody,
    user: User = Depends(page_reviewer),
    session: AsyncSession = Depends(get_session),
) -> PageDecisionReply:
    decided = await _changed(session, decide_page(session, user, proposal_id, body, now=_now()))
    await refresh_pages(decided.owners)
    embed = router_embedder(Principal(user_id=user.id, role=user.role))
    for made in decided.decided:
        await embed_decided(session, embed, made)
    return PageDecisionReply(decision=decided.decision, message=decided.message, open=decided.open)


def _now() -> datetime:
    return datetime.now(UTC)


async def _read[T](reading: Awaitable[T]) -> T:
    try:
        return await reading
    except UnknownItem as missing:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(missing)) from None
    except (OwnItem, NotYourQueue) as refused:
        raise HTTPException(status.HTTP_403_FORBIDDEN, str(refused)) from None


async def _changed[T](session: AsyncSession, change: Awaitable[T]) -> T:
    try:
        result = await _read(change)
    except HTTPException:
        await session.rollback()
        raise
    except DecisionConflict as conflict:
        await session.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, str(conflict)) from None
    except InvalidInput as invalid:
        await session.rollback()
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(invalid)) from None
    await session.commit()
    return result
