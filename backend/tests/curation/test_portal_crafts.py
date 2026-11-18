from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any, cast

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import InvalidInput
from app.curation.check_file import check_file_text
from app.curation.checks import default_context
from app.curation.dossier import Dossier
from app.curation.files import checked_dossier
from app.data.craft_master_loader import load_master, master_categories, seed_uuid
from app.data.curation_scopes import CraftScope, category_scopes, craft_scopes
from app.data.district_register import load_district_register
from app.data.portal_craft_register import PortalCraft, load_portal_crafts, parse_portal_crafts
from app.services.curation_import import ImportReport, import_path
from app.services.curation_preview import master_craft, preview_page

from .builders import check_for, passing_plain

PORTAL_SLUGS = {
    "Bishnupur-Terracotta-Craft",
    "Cane-And-Bamboo",
    "Dabu-Hand-Block-Printing",
    "Ghurni-Clay-Doll-Craft",
    "Krishnanagar-Terracotta",
    "Meghalaya-Stone-Carving",
    "Mysuru-Stone-Carving",
}


def register_row(**changes: Any) -> dict[str, Any]:
    row = {
        "slug": "Test-Portal-Craft",
        "name": "Test Portal Craft",
        "subCategorySlug": None,
        "stateOfOrigin": [],
        "stateOfPractice": ["All India"],
        "giStatus": "NON_GI",
        "portals": ["FIELD_REPOSITORY"],
        "status": "ACTIVE",
        "mergedInto": None,
    }
    return row | changes


def test_the_register_holds_the_portal_crafts_off_the_master_list() -> None:
    crafts = load_portal_crafts()
    master = {craft.slug for craft in load_master()}
    subs = {sub.slug for category in master_categories() for sub in category.sub_categories}
    states = load_district_register().states
    assert {craft.slug for craft in crafts} == PORTAL_SLUGS
    assert len(crafts) == len(PORTAL_SLUGS)
    for craft in crafts:
        assert craft.slug not in master
        assert craft.sub_category_slug is None or craft.sub_category_slug in subs
        assert set(craft.state_of_origin) | set(craft.state_of_practice) <= states
        assert craft.merged_into is None or craft.merged_into in master
        assert set(craft.portals) <= {"DESIGNER", "FIELD_REPOSITORY"}


def test_scopes_mark_merged_portal_crafts_and_family_crafts() -> None:
    scopes = craft_scopes()
    assert scopes["Krishnanagar-Terracotta"] == CraftScope(
        "Krishnanagar-Terracotta",
        "Krishnanagar Terracotta",
        family=False,
        category_slug="Mud-Based-Craft-Category",
    )
    assert (scopes["Cane-And-Bamboo"].merged_into, scopes["Cane-And-Bamboo"].category_slug) == (
        "Cane-Bamboo-Craft",
        None,
    )
    assert scopes["Mysuru-Stone-Carving"].category_slug == "Stone-Craft-Category"
    assert [
        slug for slug in ("Other-Stone-Carving", "Stone-Others", "Cane-Bamboo-Craft") if scopes[slug].family
    ] == [
        "Other-Stone-Carving",
        "Stone-Others",
        "Cane-Bamboo-Craft",
    ]
    assert not scopes["Kutch-Ajrakh"].family
    assert sum(1 for scope in scopes.values() if scope.family) == 81


def test_the_register_refuses_rows_off_its_shape() -> None:
    with pytest.raises(ValueError, match="names mergedInto"):
        parse_portal_crafts({"crafts": [register_row(status="MERGED")]})
    with pytest.raises(ValueError, match="names mergedInto"):
        parse_portal_crafts({"crafts": [register_row(mergedInto="Cane-Bamboo-Craft")]})
    with pytest.raises(ValueError, match="has status LEGACY"):
        parse_portal_crafts({"crafts": [register_row(status="LEGACY")]})
    twin = parse_portal_crafts({"crafts": [register_row(slug="Kutch-Ajrakh")]})
    with pytest.raises(ValueError, match="already on the master list"):
        craft_scopes(portal=twin)
    family: tuple[PortalCraft, ...] = parse_portal_crafts({"crafts": [register_row()]})
    assert craft_scopes(master=(), portal=family)["Test-Portal-Craft"].family


def test_the_preview_builds_a_portal_craft_with_the_id_the_portal_sync_gives_it() -> None:
    craft, names = master_craft("Krishnanagar-Terracotta")
    assert craft.id == uuid.UUID(seed_uuid("c", "Krishnanagar-Terracotta"))
    assert (craft.name, craft.category, craft.giStatus, craft.stateOfPractice) == (
        "Krishnanagar Terracotta",
        "Mud based Craft Category",
        "NON_GI",
        ["West Bengal"],
    )
    assert names == ("Mud based Craft Category", "Terracotta & Pottery works")
    with pytest.raises(InvalidInput, match="Cane-And-Bamboo is not an active craft"):
        master_craft("Cane-And-Bamboo")
    with pytest.raises(InvalidInput, match="Not-A-Craft is not an active craft"):
        master_craft("Not-A-Craft")


def test_a_portal_craft_dossier_passes_the_import_gate_and_previews(tmp_path: Path) -> None:
    plain = passing_plain()
    plain["craftSlug"] = "Krishnanagar-Terracotta"
    dossier = Dossier.model_validate(plain)
    path = tmp_path / "Krishnanagar-Terracotta.json"
    path.write_text(json.dumps(plain, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    check = check_for(dossier)
    (tmp_path / "Krishnanagar-Terracotta.check.json").write_text(
        check_file_text(check), encoding="utf-8", newline="\n"
    )
    result = checked_dossier(path, default_context())
    assert result.problems == ()
    page = preview_page(dossier, check)
    assert (page.craft.slug, page.craft.name) == ("Krishnanagar-Terracotta", "Krishnanagar Terracotta")
    assert len(page.claims) == len(plain["claims"])


class NoCrafts:
    async def scalar(self, statement: Any) -> None:
        return None


async def test_a_portal_craft_the_database_lacks_waits_instead_of_refusing(tmp_path: Path) -> None:
    plain = passing_plain()
    plain["craftSlug"] = "Krishnanagar-Terracotta"
    path = tmp_path / "Krishnanagar-Terracotta.json"
    path.write_text(json.dumps(plain, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    check = check_for(Dossier.model_validate(plain))
    (tmp_path / "Krishnanagar-Terracotta.check.json").write_text(
        check_file_text(check), encoding="utf-8", newline="\n"
    )
    outcome = await import_path(cast(AsyncSession, NoCrafts()), path, default_context())
    assert (outcome.status, outcome.craft_slug, outcome.problems) == (
        "WAITING",
        "Krishnanagar-Terracotta",
        (
            "Krishnanagar-Terracotta is a portal-added craft the database does not hold yet; "
            "the portal craft sync adds it",
        ),
    )
    report = ImportReport(withdrawn_edges=0, dossiers=(outcome,))
    assert (report.refused, report.summary()["waiting"]) == ([], 1)


def test_categories_are_the_master_list_categories_with_their_sub_categories() -> None:
    categories = category_scopes()
    assert list(categories) == [
        "Textiles-Based-Craft-Category",
        "Metal-Craft-Category",
        "Stone-Craft-Category",
        "Wood-Craft-Category",
        "Leather-Craft-Category",
        "Natural-Fibre-Grass-Work",
        "Mud-Based-Craft-Category",
        "Paper-Craft-Category",
        "Miscellaneous",
    ]
    stone = categories["Stone-Craft-Category"]
    assert stone.name == "Stone Craft Category"
    assert [(sub.slug, sub.name) for sub in stone.sub_categories] == [
        ("Stone-Carving", "Stone (Carving)"),
        ("Stone-Inlay", "Stone (Inlay)"),
        ("Stone-Others", "Stone (Others)"),
    ]
    assert sum(len(category.sub_categories) for category in categories.values()) == 36
