from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.proposal_deps import proposed
from app.core.db import get_session
from app.core.deps import require
from app.core.errors import ExternalFailure, InvalidInput, Refused
from app.core.roles import Capability
from app.models import User
from app.research.knowledge_writes import FactProposal, ProposalReply
from app.research.review_switch import CONTRIBUTION, ReviewSwitchUpdate, ReviewSwitchView
from app.services import app_settings, audit
from app.services.own_proposals import require_terms

router = APIRouter(prefix="/knowledge", tags=["knowledge"])
proposer = require(Capability.PROPOSE_KNOWLEDGE)
switch_keeper = require(Capability.REVIEW_CONTRIBUTIONS)

CHECKS_UNAVAILABLE = "The checks could not run just now; nothing was stored. Try again in a minute."
SWITCH_ACTION = "settings.review_switch_updated"


@router.post("/facts")
async def propose(
    body: FactProposal, user: User = Depends(proposer), session: AsyncSession = Depends(get_session)
) -> ProposalReply:
    try:
        await require_terms(session, user)
        return await proposed(session, body, user, CONTRIBUTION)
    except InvalidInput as error:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(error)) from None
    except Refused as error:
        raise HTTPException(status.HTTP_403_FORBIDDEN, error.message) from None
    except ExternalFailure:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, CHECKS_UNAVAILABLE) from None


@router.get("/review-switch")
async def get_review_switch(
    _: User = Depends(switch_keeper), session: AsyncSession = Depends(get_session)
) -> ReviewSwitchView:
    return ReviewSwitchView(current=await app_settings.review_switch(session))


@router.put("/review-switch")
async def set_review_switch(
    body: ReviewSwitchUpdate,
    actor: User = Depends(switch_keeper),
    session: AsyncSession = Depends(get_session),
) -> ReviewSwitchView:
    switch = await app_settings.set_review_switch(session, body, actor.id)
    await audit.record(
        session,
        action=SWITCH_ACTION,
        actor=actor,
        target_type="AppSetting",
        target_id=app_settings.REVIEW_SWITCH,
        detail={"switch": switch.stored()},
    )
    await session.commit()
    return ReviewSwitchView(current=switch)
