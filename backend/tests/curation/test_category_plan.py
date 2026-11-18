from __future__ import annotations

import hashlib
import uuid
from pathlib import Path
from typing import Any, cast

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import InvalidInput
from app.curation.checks import default_context
from app.curation.files import checked_dossier
from app.data.craft_master_loader import ID_NAMESPACE, load_master
from app.data.curation_scopes import category_scopes, craft_scopes
from app.services.category_import import import_category_path
from app.services.category_plan import CATEGORY_PLAN_PARTS, CategoryTarget, category_plan
from app.services.category_register import register_categories

from .builders import check_for, passing_dossier
from .category_support import (
    LEATHER,
    copy_fixture,
    dropped_version,
    leather_checked,
    leather_plain,
    leather_plan,
    registered,
    write_category,
)

SEED_CATEGORY_ID = uuid.uuid5(ID_NAMESPACE, "cmk" + hashlib.md5(b"k:Leather-Craft-Category").hexdigest()[:22])


def curation_id(*parts: str) -> uuid.UUID:
    return uuid.uuid5(ID_NAMESPACE, ":".join(("curation", LEATHER, *parts)))


def test_claims_and_sources_take_the_curation_ids_of_their_category() -> None:
    plain = leather_plain()
    plan = leather_plan()
    assert {row["id"] for row in plan.part("claims")} == {
        curation_id(claim["id"]) for claim in plain["claims"]
    }
    assert {row["id"] for row in plan.part("sources")} == {curation_id(s["id"]) for s in plain["sources"]}
    assert len(plan.part("claimSources")) == sum(len(claim["quotes"]) for claim in plain["claims"])
    assert {row["status"] for row in plan.part("claims")} == {"APPROVED"}
    levels = {row["id"]: row["evidenceLevel"] for row in plan.part("claims")}
    assert levels[curation_id("C040")] == "HYPOTHESIS" and levels[curation_id("C001")] == "PROVISIONAL"


def test_every_claim_is_marked_as_the_category_s_own_and_no_concept_belongs_to_a_craft() -> None:
    plain = leather_plain()
    plan = leather_plan()
    category = registered(LEATHER).id
    marks = {
        row["claimId"]: (row["categoryId"], row["key"], row["discipline"])
        for row in plan.part("curatedClaims")
    }
    assert marks == {
        curation_id(claim["id"]): (category, claim["id"], claim["discipline"]) for claim in plain["claims"]
    }
    concepts = plan.part("concepts")
    assert {(row["craftId"], row["subCategoryId"]) for row in concepts} == {(None, None)}
    assert all(row["originRef"].startswith(f"curation:{LEATHER}:") for row in concepts)
    overview = next(row for row in concepts if row["originRef"] == f"curation:{LEATHER}:craft:OVERVIEW")
    assert (overview["type"], overview["name"]) == ("TRADITION", "Leather Craft Category")


def test_the_plan_holds_evidence_pictures_and_glossary_only() -> None:
    plain = leather_plain()
    plan = leather_plan()
    assert tuple(plan.rows) == CATEGORY_PLAN_PARTS
    assert len(plan.part("media")) == len(plain["pictures"]) == 2
    assert {row["mediaRefId"] for row in plan.part("mediaClaims")} == {
        row["id"] for row in plan.part("media")
    }
    assert {row["key"] for row in plan.part("terms")} == {"tholu-bommalata", "togalu-gombeyata", "charmakara"}
    assert len(plan.part("termConcepts")) == len(plain["glossary"])
    assert plan.index.category_slug == LEATHER and plan.index.coverage == "THIN"
    assert [question.key for question in plan.index.open_questions] == ["O01"]


def test_a_source_another_row_holds_is_cited_through_that_row() -> None:
    plan = leather_plan()
    kept = uuid.UUID(int=7)
    aliased = plan.with_sources({curation_id("S01"): kept})
    assert curation_id("S01") not in {row["id"] for row in aliased.part("sources")}
    cited = {row["sourceId"] for row in aliased.part("claimSources")}
    assert kept in cited and curation_id("S01") not in cited
    assert plan.with_sources({}) is plan


def test_the_plan_refuses_a_dossier_of_another_scope_or_category() -> None:
    dossier, check = leather_checked()
    paper = CategoryTarget(id=uuid.UUID(int=1), slug="Paper-Craft-Category", name="Paper Craft Category")
    with pytest.raises(InvalidInput, match="not the category dossier of Paper-Craft-Category"):
        category_plan(dossier, check, paper)
    craft = passing_dossier()
    with pytest.raises(InvalidInput, match="not the category dossier"):
        category_plan(craft, check_for(craft), CategoryTarget(id=uuid.UUID(int=1), slug=LEATHER, name="x"))


def test_the_register_holds_the_nine_master_categories_with_their_crafts() -> None:
    categories = register_categories()
    assert [category.slug for category in categories] == list(category_scopes())
    leather = registered(LEATHER)
    assert leather.id == SEED_CATEGORY_ID
    master = [craft for craft in load_master() if craft.category_slug == LEATHER]
    assert leather.member_slugs() == {craft.slug for craft in master}
    assert leather.craft_count() == sum(1 for craft in master if not craft.is_catch_all) == 6
    labels = {category.slug: category.label for category in categories}
    assert (labels[LEATHER], labels["Mud-Based-Craft-Category"], labels["Textiles-Based-Craft-Category"]) == (
        "Leather",
        "Clay",
        "Textiles",
    )


def test_members_run_curated_then_gi_then_by_name_with_catch_alls_last() -> None:
    footwear = registered(LEATHER).sub_categories[0]
    assert [craft.slug for craft in footwear.crafts] == [
        "Chamba-Chappal",
        "Kolhapuri-Chappal",
        "Kataki-Chappal",
        "Other-Leather-Footwear",
    ]
    curated = next(c for c in register_categories(curated={"Kataki-Chappal"}) if c.slug == LEATHER)
    assert curated.sub_categories[0].crafts[0].slug == "Kataki-Chappal"


def test_no_category_slug_is_a_craft_slug_so_curation_ids_cannot_meet() -> None:
    assert set(category_scopes()).isdisjoint(craft_scopes())


class NoSession:
    async def scalar(self, statement: Any) -> None:
        raise AssertionError("a refused dossier never reaches the database")


async def test_a_category_dossier_without_a_current_check_file_is_refused(tmp_path: Path) -> None:
    path = copy_fixture(tmp_path)
    path.with_name(f"{LEATHER}.check.json").unlink()
    outcome = await import_category_path(cast(AsyncSession, NoSession()), path, default_context())
    assert (outcome.status, outcome.file) == ("REFUSED", f"categories/{LEATHER}.json")
    assert outcome.problems == (
        f"categories/{LEATHER}.json: check file: {LEATHER}.check.json is missing; run verify",
    )


async def test_a_category_dossier_that_fails_its_checks_is_refused(tmp_path: Path) -> None:
    plain = leather_plain()
    plain["overview"]["lede"][1] = dict(plain["overview"]["lede"][1], subCategories=["Leather-Footwear"])
    plain["overview"]["sections"][0]["sentences"][3]["subCategories"] = []
    plain["overview"]["sections"][0]["sentences"][4]["subCategories"] = []
    path = write_category(tmp_path, plain)
    outcome = await import_category_path(cast(AsyncSession, NoSession()), path, default_context())
    assert outcome.status == "REFUSED"
    assert any("sub-category Leather-Other-Articles" in line for line in outcome.problems)


def test_a_later_version_without_one_claim_passes_its_checks(tmp_path: Path) -> None:
    path = dropped_version(tmp_path, "C170")
    result = checked_dossier(path, default_context())
    assert result.problems == ()
    assert result.dossier is not None and result.dossier.version == 2
    assert "C170" not in {claim.id for claim in result.dossier.claims}
