from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Path, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.deps import require
from app.core.roles import Capability
from app.models import User
from app.research.blocks import BLOCK_ID_MAX_CHARS, BLOCK_ID_PATTERN
from app.schemas.simulation_hiding import HiddenSimulation, SimulationHiding
from app.services.simulation_hiding import SimulationHide, set_simulation_hidden

router = APIRouter(prefix="/answers", tags=["simulations"])

NOT_KEPT_DETAIL = "That generated explainer is not in your answers."


@router.put("/{answer_id}/simulations/{block_id}/hidden")
async def simulation_hidden(
    answer_id: uuid.UUID,
    body: SimulationHiding,
    block_id: str = Path(max_length=BLOCK_ID_MAX_CHARS, pattern=BLOCK_ID_PATTERN),
    *,
    user: User = Depends(require(Capability.HIDE_GENERATED)),
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    change = SimulationHide(answer_id=answer_id, block_id=block_id, hidden=body.hidden)
    marked = await set_simulation_hidden(session, change, user=user, now=datetime.now(UTC))
    if marked is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, NOT_KEPT_DETAIL)
    shown = HiddenSimulation(
        answer_id=answer_id, block_id=block_id, piece_id=marked.piece_id, hidden=marked.hidden
    )
    return shown.model_dump(mode="json", by_alias=True)
