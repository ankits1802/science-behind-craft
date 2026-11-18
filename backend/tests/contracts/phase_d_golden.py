import json
from functools import cache
from typing import Any, Literal

from pydantic import Field

from app.research.base import ContractModel
from app.research.citations import SourceRef
from app.research.crafts import CraftRef

from .golden import golden_json
from .phase_b_golden import FixturePiece, FixtureSection

__all__ = [
    "PHASE_D",
    "PhaseDFixture",
    "phase_d",
    "phase_d_blocks",
]

PHASE_D = "explainer.phase-d.golden.json"


class PhaseDFixture(ContractModel):
    schema_version: Literal[1]
    crafts: list[CraftRef] = Field(min_length=2, max_length=2)
    sections: list[FixtureSection] = Field(min_length=1)
    pieces: list[FixturePiece]
    sources: list[SourceRef]


@cache
def _phase_d() -> str:
    return json.dumps(golden_json(PHASE_D))


def phase_d() -> dict[str, Any]:
    return json.loads(_phase_d())


def phase_d_blocks() -> dict[str, dict[str, Any]]:
    return {block["id"]: block for section in phase_d()["sections"] for block in section["blocks"]}
