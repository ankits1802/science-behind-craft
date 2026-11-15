from typing import Any

import pytest

from app.data.craft_master_loader import build_catalogue, seed_plan
from app.services.craft_catalogue import (
    assemble_catalogue,
    etag_matches,
    quoted_etag,
    reference_tables,
)


@pytest.fixture(scope="module")
def plan() -> dict[str, Any]:
    return seed_plan()


def _assemble(plan: dict[str, Any], **kwargs: Any) -> dict[str, Any]:
    return assemble_catalogue(
        plan["categories"],
        plan["subCategories"],
        plan["crafts"],
        plan["spellings"],
        plan["aliases"],
        **kwargs,
    )


def test_database_catalogue_matches_the_file_catalogue(plan: dict[str, Any]) -> None:
    live = _assemble(plan)
    files = build_catalogue()
    assert set(live) == set(files) == {"version", "categories", "crafts"}
    assert live["categories"] == files["categories"]
    assert sorted(live["crafts"], key=lambda c: c["id"]) == sorted(files["crafts"], key=lambda c: c["id"])
    assert all(set(row) == set(files["crafts"][0]) for row in live["crafts"])


def test_crafts_follow_category_then_serial_order(plan: dict[str, Any]) -> None:
    live = _assemble(plan)
    place = {
        sub["id"]: (category["sortOrder"], sub["sortOrder"])
        for category in live["categories"]
        for sub in category["subCategories"]
    }
    keys = [(place[c["subCategoryId"]], c["sourceSerial"] or 0) for c in live["crafts"]]
    assert keys == sorted(keys)


def test_version_is_stable_and_moves_on_change(plan: dict[str, Any]) -> None:
    first = _assemble(plan)["version"]
    assert _assemble(plan)["version"] == first
    renamed = [dict(c) for c in plan["crafts"]]
    renamed[0]["name"] = renamed[0]["name"] + " revised"
    moved = assemble_catalogue(
        plan["categories"], plan["subCategories"], renamed, plan["spellings"], plan["aliases"]
    )["version"]
    assert moved != first
    assert _assemble(plan, include_inactive=True)["version"] != first


def test_inactive_crafts_are_hidden_unless_asked(plan: dict[str, Any]) -> None:
    crafts = [dict(c) for c in plan["crafts"]]
    retired = crafts[0]
    retired["status"] = "LEGACY"
    args = (plan["categories"], plan["subCategories"], crafts, plan["spellings"], plan["aliases"])
    active = assemble_catalogue(*args)
    assert retired["id"] not in {c["id"] for c in active["crafts"]}
    assert "status" not in active["crafts"][0]
    full = assemble_catalogue(*args, include_inactive=True, references={retired["id"]: 3})
    assert full["crafts"][-1]["id"] == retired["id"]
    assert full["crafts"][-1]["status"] == "LEGACY"
    assert full["crafts"][-1]["referenceCount"] == 3
    assert full["crafts"][0]["referenceCount"] is None
    total_active = sum(s["craftCount"] for c in full["categories"] for s in c["subCategories"])
    assert total_active == len(crafts) - 1


def test_rejected_aliases_are_left_out(plan: dict[str, Any]) -> None:
    craft = plan["crafts"][0]
    aliases = [{"craftId": craft["id"], "aliasNorm": "zz hidden", "status": "REJECTED"}]
    live = assemble_catalogue(plan["categories"], plan["subCategories"], plan["crafts"], [], aliases)
    assert "zz hidden" not in next(c for c in live["crafts"] if c["id"] == craft["id"])["aliases"]


@pytest.mark.parametrize(
    ("header", "matches"),
    [
        ('"abc"', True),
        ('W/"abc"', True),
        ('"x", "abc"', True),
        ("*", True),
        ('"x"', False),
        (None, False),
        ("", False),
    ],
)
def test_etag_matching(header: str | None, matches: bool) -> None:
    assert etag_matches(header, quoted_etag("abc")) is matches


def test_reference_tables_skip_the_craft_and_its_aliases() -> None:
    names = {table.name for table in reference_tables()}
    assert "CraftAlias" not in names
    assert "Craft" not in names
    assert "CraftLocation" in names
