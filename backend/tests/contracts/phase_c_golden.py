import json
import uuid
from functools import cache
from typing import Any, Literal

from pydantic import Field

from app.research.base import ContractModel
from app.research.citations import SourceRef
from app.research.crafts import CraftRef
from app.research.explainer import SECTION_ID_PATTERN, Block
from app.research.subject_keys import TopicKey
from app.research.vocabulary import Discipline

from .golden import golden_json

__all__ = [
    "CORPUS",
    "PHASE_C",
    "FixturePiece",
    "FixtureSection",
    "PhaseCFixture",
    "SandboxFrame",
    "corpus",
    "phase_c",
    "phase_c_blocks",
]

PHASE_C = "explainer.phase-c.golden.json"
CORPUS = "sandbox.corpus.golden.json"


class SandboxFrame(ContractModel):
    attribute: str
    csp: str
    data_element_id: str
    max_bytes: int


class FixtureSection(ContractModel):
    id: str = Field(pattern=SECTION_ID_PATTERN)
    discipline: Discipline
    blocks: list[Block] = Field(min_length=1)


class FixturePiece(ContractModel):
    block_id: str
    craft_id: uuid.UUID | None
    facet: Discipline
    topic_key: TopicKey


class PhaseCFixture(ContractModel):
    schema_version: Literal[1]
    craft: CraftRef
    sandbox: SandboxFrame
    sections: list[FixtureSection] = Field(min_length=1)
    pieces: list[FixturePiece]
    sources: list[SourceRef]


@cache
def _text(name: str) -> str:
    return json.dumps(golden_json(name))


def phase_c() -> dict[str, Any]:
    return json.loads(_text(PHASE_C))


def corpus() -> dict[str, Any]:
    return json.loads(_text(CORPUS))


def phase_c_blocks() -> dict[str, dict[str, Any]]:
    return {block["id"]: block for section in phase_c()["sections"] for block in section["blocks"]}
