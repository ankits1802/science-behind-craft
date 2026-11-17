import ast
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

from .golden import REPO, golden_json

__all__ = [
    "PHASE_B",
    "FixturePiece",
    "FixtureSection",
    "PhaseBFixture",
    "Placeholders",
    "catalog_dataset",
    "phase_b",
    "phase_b_blocks",
]

PHASE_B = "explainer.phase-b.golden.json"
GEO_CATALOG = REPO / "etl" / "geo" / "geo_etl" / "catalog.py"
DATASET_FIELDS = (
    "code",
    "title",
    "publisher",
    "edition",
    "period",
    "nativeResolution",
    "licence",
    "licenceUrl",
    "attribution",
    "citation",
    "url",
)


class Placeholders(ContractModel):
    main_riv: int = Field(ge=1)
    reach_ids: list[int] = Field(min_length=1)


class FixtureSection(ContractModel):
    id: str = Field(pattern=SECTION_ID_PATTERN)
    discipline: Discipline
    blocks: list[Block] = Field(min_length=1)


class FixturePiece(ContractModel):
    block_id: str
    craft_id: uuid.UUID | None
    facet: Discipline
    topic_key: TopicKey


class PhaseBFixture(ContractModel):
    schema_version: Literal[1]
    craft: CraftRef
    placeholders: Placeholders
    sections: list[FixtureSection] = Field(min_length=1)
    pieces: list[FixturePiece]
    sources: list[SourceRef]


@cache
def _phase_b() -> str:
    return json.dumps(golden_json(PHASE_B))


def phase_b() -> dict[str, Any]:
    return json.loads(_phase_b())


def phase_b_blocks() -> dict[str, dict[str, Any]]:
    return {block["id"]: block for section in phase_b()["sections"] for block in section["blocks"]}


def catalog_dataset(code: str) -> dict[str, Any]:
    tree = ast.parse(GEO_CATALOG.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "Dataset":
            fields = {kw.arg: ast.literal_eval(kw.value) for kw in node.keywords if kw.arg}
            if fields.get("code") == code:
                return {key: fields.get(key) for key in DATASET_FIELDS}
    raise AssertionError(f"{code} is not a dataset of the geo ETL catalogue")
