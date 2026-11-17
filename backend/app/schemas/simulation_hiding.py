from __future__ import annotations

import uuid

from pydantic import Field

from app.research.base import ContractModel
from app.research.blocks import BLOCK_ID_MAX_CHARS, BLOCK_ID_PATTERN

__all__ = ["HiddenSimulation", "SimulationHiding"]


class SimulationHiding(ContractModel):
    hidden: bool


class HiddenSimulation(ContractModel):
    answer_id: uuid.UUID
    block_id: str = Field(max_length=BLOCK_ID_MAX_CHARS, pattern=BLOCK_ID_PATTERN)
    piece_id: uuid.UUID
    hidden: bool
