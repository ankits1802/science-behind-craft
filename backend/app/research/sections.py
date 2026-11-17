from __future__ import annotations

from collections.abc import Mapping, Sequence
from types import MappingProxyType
from typing import Annotated, Literal

from pydantic import Field

from app.models.enums import DISCIPLINES

from .base import ContractModel
from .composition import HEADING_MAX_CHARS
from .depth import depth_policy
from .explainer import SECTION_ID_PATTERN
from .planning import RetrievalPlan
from .vocabulary import Discipline

__all__ = [
    "ANSWER_PLANS_SCHEMA_VERSION",
    "DISCIPLINE_FIELDS",
    "DISCIPLINE_TITLES",
    "FALLBACK_DISCIPLINE",
    "LADDER_DISCIPLINE",
    "AnswerPlans",
    "SectionPlan",
    "SectionSpec",
    "block_id",
    "section_specs",
]

ANSWER_PLANS_SCHEMA_VERSION = 1
FALLBACK_DISCIPLINE = "OVERVIEW"
LADDER_DISCIPLINE = "PROCESS"
DISCIPLINE_TITLES: Mapping[str, str] = MappingProxyType(
    {
        "OVERVIEW": "What it is",
        "PROCESS": "How it is made",
        "CHEMISTRY": "The chemistry",
        "PHYSICS": "The physics",
        "MATERIALS": "Materials",
        "GEOGRAPHY": "Geography and water",
        "GEOLOGY": "Geology and soil",
        "CLIMATE": "Climate",
        "ECOLOGY": "Ecology",
        "BOTANY": "Dye and fibre plants",
        "HISTORY": "History",
        "ECONOMICS": "Economics",
        "DESIGN": "Design",
        "HEALTH": "Health and safety",
    }
)
DISCIPLINE_FIELDS: Mapping[str, str] = MappingProxyType(
    {
        "OVERVIEW": "what the craft is, where and by whom it is practised",
        "PROCESS": "how the craft is made, stage by stage",
        "CHEMISTRY": "chemistry",
        "PHYSICS": "physics",
        "MATERIALS": "materials science",
        "GEOGRAPHY": "geography and water",
        "GEOLOGY": "geology and soil",
        "CLIMATE": "climate",
        "ECOLOGY": "ecology",
        "BOTANY": "botany of dye and fibre plants",
        "HISTORY": "history",
        "ECONOMICS": "economics and markets",
        "DESIGN": "design and art history",
        "HEALTH": "health, toxicology and safe handling",
    }
)

SectionId = Annotated[str, Field(pattern=SECTION_ID_PATTERN)]


class SectionSpec(ContractModel):
    id: SectionId
    discipline: Discipline
    title: str = Field(min_length=1, max_length=HEADING_MAX_CHARS)
    order: int = Field(ge=1)


class SectionPlan(ContractModel):
    section_id: SectionId
    discipline: Discipline
    plan: RetrievalPlan


class AnswerPlans(ContractModel):
    schema_version: Literal[1] = ANSWER_PLANS_SCHEMA_VERSION
    sections: list[SectionPlan]


def section_specs(disciplines: Sequence[str], depth: str) -> list[SectionSpec]:
    chosen = [d for d in dict.fromkeys(disciplines) if d in DISCIPLINES][: depth_policy(depth).max_sections]
    return [
        SectionSpec(id=f"s{order}", discipline=discipline, title=DISCIPLINE_TITLES[discipline], order=order)
        for order, discipline in enumerate(chosen or [FALLBACK_DISCIPLINE], start=1)
    ]


def block_id(section_id: str, ordinal: int) -> str:
    return f"{section_id}.b{ordinal}"
