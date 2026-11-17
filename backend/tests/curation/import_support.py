from __future__ import annotations

import json
import uuid
from functools import cache
from typing import Any

from app.curation.checks import default_context
from app.curation.files import CURATION_DIR, DossierResult, checked_dossier
from app.data.craft_master_loader import ID_NAMESPACE
from app.data.district_register import load_district_codes
from app.services.curation_plan import CurationPlan, curation_plan
from app.services.curation_preview import master_craft
from app.services.curation_rows import CraftTarget

AJRAKH = "Kutch-Ajrakh"
AJRAKH_GOLDEN = "craft.page.golden.json"


def expected_id(text: str) -> uuid.UUID:
    return uuid.uuid5(ID_NAMESPACE, text)


@cache
def checked(slug: str) -> DossierResult:
    result = checked_dossier(CURATION_DIR / f"{slug}.json", default_context())
    assert result.problems == (), result.problems
    return result


def raw(slug: str) -> dict[str, Any]:
    return json.loads((CURATION_DIR / f"{slug}.json").read_text(encoding="utf-8"))


def target(slug: str) -> CraftTarget:
    craft, _names = master_craft(slug)
    return CraftTarget(id=craft.id, slug=craft.slug, name=craft.name)


@cache
def plan_of(slug: str) -> CurationPlan:
    result = checked(slug)
    assert result.dossier is not None and result.check is not None
    return curation_plan(result.dossier, result.check, target(slug), load_district_codes())
