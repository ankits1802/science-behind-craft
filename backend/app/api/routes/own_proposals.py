from __future__ import annotations

import uuid
from collections.abc import Awaitable
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.proposal_limits import proposal_limit
from app.core.db import get_session
from app.core.deps import require
from app.core.errors import InvalidInput, Refused
from app.core.rate_limit import COMPONENT_PROPOSALS
from app.core.roles import Capability
from app.models import User
from app.research.component_proposals import ComponentProposalResult
from app.research.knowledge_api import CraftComponents
from app.research.own_proposals import (
    ComponentProposalBody,
    LibrarySearch,
    OwnProposal,
    OwnProposals,
    ProposalForm,
    TermsAcceptance,
    TermsStatus,
)
from app.services import component_library, own_proposals
from app.services.page_revalidation import refresh_pages

router = APIRouter(prefix="/contributions/proposals", tags=["contributions"])
contributor = require(Capability.PROPOSE_KNOWLEDGE)


@router.get("/mine")
async def my_proposals(
    user: User = Depends(contributor), session: AsyncSession = Depends(get_session)
) -> OwnProposals:
    return await own_proposals.own_proposals(session, user)


@router.post("/facts/{claim_id}/withdraw")
async def withdraw_fact(
    claim_id: uuid.UUID, user: User = Depends(contributor), session: AsyncSession = Depends(get_session)
) -> OwnProposal:
    return await _written(session, own_proposals.withdraw_fact(session, user, claim_id))


@router.post("/components/{proposal_id}/withdraw")
async def withdraw_component(
    proposal_id: uuid.UUID, user: User = Depends(contributor), session: AsyncSession = Depends(get_session)
) -> OwnProposal:
    withdrawing = own_proposals.withdraw_component(session, user, proposal_id, now=datetime.now(UTC))
    withdrawn = await _written(session, withdrawing)
    await refresh_pages(withdrawn.owners)
    return withdrawn.item


@router.post("/components", dependencies=[Depends(proposal_limit(COMPONENT_PROPOSALS, contributor))])
async def propose_component(
    body: ComponentProposalBody,
    user: User = Depends(contributor),
    session: AsyncSession = Depends(get_session),
) -> ComponentProposalResult:
    proposed = own_proposals.propose_on_site(session, user, body, now=datetime.now(UTC))
    return await _written(session, proposed)


@router.get("/library")
async def search_library(
    search: Annotated[LibrarySearch, Query()],
    _: User = Depends(contributor),
    session: AsyncSession = Depends(get_session),
) -> CraftComponents:
    try:
        return await component_library.library_components(
            session, slug=search.craft_slug, field=search.field, kind=search.kind, query=search.query
        )
    except InvalidInput as invalid:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(invalid)) from invalid


@router.get("/form")
async def proposal_form(
    user: User = Depends(contributor), session: AsyncSession = Depends(get_session)
) -> ProposalForm:
    return await own_proposals.proposal_form(session, user)


@router.post("/terms")
async def accept_terms(
    body: TermsAcceptance, user: User = Depends(contributor), session: AsyncSession = Depends(get_session)
) -> TermsStatus:
    return await _written(session, own_proposals.accept_terms(session, user, body))


async def _written[Answer](session: AsyncSession, change: Awaitable[Answer]) -> Answer:
    try:
        answer = await change
    except own_proposals.UnknownProposal as missing:
        await session.rollback()
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(missing)) from missing
    except Refused as refused:
        await session.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, refused.message) from refused
    except InvalidInput as invalid:
        await session.rollback()
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(invalid)) from invalid
    await session.commit()
    return answer
