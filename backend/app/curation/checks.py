from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from app.data.craft_master_loader import load_master
from app.data.district_register import DistrictRegister, load_district_register

from .check_file import CheckFile, check_file_problems
from .claim_rules import claim_problems
from .coverage import coverage_problems
from .dossier import Dossier
from .entity_rules import (
    community_problems,
    market_problems,
    picture_problems,
    place_problems,
    reaction_problems,
    stage_problems,
)
from .overview_rules import overview_problems
from .problems import Problem
from .references import id_problems, reference_problems
from .source_rules import personal_data_problems, source_problems

__all__ = ["DOSSIER_RULES", "CheckContext", "content_problems", "default_context", "dossier_problems"]

DOSSIER_RULES: tuple[Callable[[Dossier], list[Problem]], ...] = (
    claim_problems,
    source_problems,
    community_problems,
    stage_problems,
    reaction_problems,
    market_problems,
    picture_problems,
    overview_problems,
    coverage_problems,
    personal_data_problems,
)


@dataclass(frozen=True)
class CheckContext:
    crafts: frozenset[str]
    districts: DistrictRegister


def default_context() -> CheckContext:
    return CheckContext(
        crafts=frozenset(craft.slug for craft in load_master()),
        districts=load_district_register(),
    )


def content_problems(dossier: Dossier, context: CheckContext) -> list[Problem]:
    found = []
    if dossier.craft_slug not in context.crafts:
        found.append(Problem("craftSlug", f"{dossier.craft_slug} is not a craft slug on the master list"))
    structure = [*id_problems(dossier), *reference_problems(dossier)]
    if structure:
        return found + structure
    for rule in DOSSIER_RULES:
        found += rule(dossier)
    return found + place_problems(dossier, context.districts)


def dossier_problems(dossier: Dossier, context: CheckContext, check: CheckFile | None) -> list[Problem]:
    return content_problems(dossier, context) + check_file_problems(dossier, check)
