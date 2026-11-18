from __future__ import annotations

import json
import shutil
from functools import cache
from pathlib import Path
from typing import Any

from app.curation.check_file import CheckFile, check_file_text, verified_digest
from app.curation.checks import default_context
from app.curation.dossier import Dossier
from app.curation.files import CATEGORIES_DIR_NAME, checked_dossier
from app.services.category_page import CategoryPageRecords
from app.services.category_plan import CategoryPlan, CategoryTarget, category_plan
from app.services.category_preview import preview_category_records
from app.services.category_register import CategoryRecord, register_categories

from .builders import FIXTURES

LEATHER = "Leather-Craft-Category"
PAPER = "Paper-Craft-Category"
LEATHER_DOSSIER = FIXTURES / CATEGORIES_DIR_NAME / f"{LEATHER}.json"
PAGE_GOLDEN = "category.page.golden.json"
UNCURATED_GOLDEN = "category.page.not-curated.golden.json"
LIST_GOLDEN = "category.list.golden.json"


def leather_plain() -> dict[str, Any]:
    return json.loads(LEATHER_DOSSIER.read_text(encoding="utf-8"))


@cache
def leather_checked() -> tuple[Dossier, CheckFile]:
    result = checked_dossier(LEATHER_DOSSIER, default_context())
    assert result.problems == (), result.problems
    assert result.dossier is not None and result.check is not None
    return result.dossier, result.check


def registered(slug: str) -> CategoryRecord:
    return next(category for category in register_categories() if category.slug == slug)


def leather_target() -> CategoryTarget:
    category = registered(LEATHER)
    return CategoryTarget(id=category.id, slug=category.slug, name=category.name)


def leather_plan() -> CategoryPlan:
    dossier, check = leather_checked()
    return category_plan(dossier, check, leather_target())


def leather_records(plain: dict[str, Any] | None = None) -> CategoryPageRecords:
    if plain is None:
        dossier, check = leather_checked()
    else:
        dossier = Dossier.model_validate(plain)
        check = recheck(leather_checked()[1], dossier)
    return preview_category_records(dossier, check, registered(LEATHER))


def recheck(check: CheckFile, dossier: Dossier) -> CheckFile:
    kept = {(claim.id, quote.source_id, quote.quote) for claim in dossier.claims for quote in claim.quotes}
    return check.model_copy(
        update={
            "dossier_version": dossier.version,
            "dossier_digest": verified_digest(dossier),
            "quotes": [
                entry for entry in check.quotes if (entry.claim_id, entry.source_id, entry.quote) in kept
            ],
        }
    )


def write_category(directory: Path, plain: dict[str, Any]) -> Path:
    folder = directory / CATEGORIES_DIR_NAME
    folder.mkdir(parents=True, exist_ok=True)
    dossier = Dossier.model_validate(plain)
    path = folder / f"{dossier.slug}.json"
    path.write_text(json.dumps(plain, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    check = recheck(leather_checked()[1], dossier)
    path.with_name(f"{dossier.slug}.check.json").write_text(
        check_file_text(check), encoding="utf-8", newline="\n"
    )
    return path


def copy_fixture(directory: Path) -> Path:
    folder = directory / CATEGORIES_DIR_NAME
    folder.mkdir(parents=True, exist_ok=True)
    shutil.copy(LEATHER_DOSSIER, folder / LEATHER_DOSSIER.name)
    check = LEATHER_DOSSIER.with_name(f"{LEATHER}.check.json")
    shutil.copy(check, folder / check.name)
    return folder / LEATHER_DOSSIER.name


def dropped_version(directory: Path, claim_key: str) -> Path:
    plain = leather_plain()
    plain["version"] = 2
    plain["claims"] = [claim for claim in plain["claims"] if claim["id"] != claim_key]
    for picture in plain["pictures"]:
        picture["claimIds"] = [key for key in picture["claimIds"] if key != claim_key]
    return write_category(directory, plain)
