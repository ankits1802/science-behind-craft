from __future__ import annotations

import uuid
from collections.abc import Awaitable
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.page_proposal_deps import page_proposed
from app.api.structure_proposal_deps import site_origin
from app.core.db import get_session
from app.core.deps import require
from app.core.errors import InvalidInput, Refused
from app.core.roles import Capability
from app.models import User
from app.research.page_holds import DISCARD, HoldDecision, PageHoldView
from app.research.page_proposals import PageBundle, PageProposalResult
from app.research.review_switch import AGENT
from app.services import page_holds
from app.services.component_lifecycle import withdrawn_owners
from app.services.page_revalidation import refresh_pages

router = APIRouter(prefix="/knowledge/pages/held", tags=["knowledge"])
proposer = require(Capability.PROPOSE_KNOWLEDGE)


@router.get("/{hold_id}")
async def read_held_page(
    hold_id: uuid.UUID, user: User = Depends(proposer), session: AsyncSession = Depends(get_session)
) -> PageHoldView:
    now = datetime.now(UTC)
    view = await _answered(session, page_holds.held_page(session, user, hold_id, site=site_origin(), now=now))
    await session.commit()
    return view


@router.post("/{hold_id}/decision")
async def decide_held_page(
    hold_id: uuid.UUID,
    body: HoldDecision,
    user: User = Depends(proposer),
    session: AsyncSession = Depends(get_session),
) -> PageHoldView:
    if body.decision == DISCARD:
        view = await _answered(session, page_holds.discard_hold(session, user, hold_id, _place()))
        await session.commit()
        return view

    async def proposed(bundle: PageBundle) -> PageProposalResult:
        return await page_proposed(session, bundle, user, origin=AGENT, site=site_origin())

    view = await _answered(session, page_holds.confirm_hold(session, user, hold_id, proposed, _place()))
    owners = await withdrawn_owners(session, view.result.parts if view.result is not None else [])
    await session.commit()
    await refresh_pages(owners)
    return view


def _place() -> page_holds.HoldPlace:
    return page_holds.HoldPlace(site=site_origin(), client_name=None, now=datetime.now(UTC))


async def _answered[Answer](session: AsyncSession, change: Awaitable[Answer]) -> Answer:
    try:
        answer = await change
    except page_holds.UnknownHold as missing:
        await session.rollback()
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(missing)) from None
    except Refused as refused:
        await session.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, refused.message) from None
    except InvalidInput as invalid:
        await session.rollback()
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(invalid)) from None
    return answer
