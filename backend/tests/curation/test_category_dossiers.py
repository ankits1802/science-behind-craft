from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from app.curation.check_file import check_file_text, verified_digest
from app.curation.checks import content_problems, default_context
from app.curation.coverage import coverage_problems, full_shortfalls
from app.curation.dossier import Dossier
from app.curation.files import category_paths, checked_dossier, dossier_paths, stray_problems

from .builders import check_for, passing_plain

STONE = "Stone-Craft-Category"
UNCOVERED = "has no overview sentence and no open question; cite one, or ask an open question saying no source was found"


def category_plain(**header: Any) -> dict[str, Any]:
    plain = passing_plain()
    del plain["craftSlug"]
    lede = plain["overview"]["lede"]
    lede[0] = dict(lede[0], subCategories=["Stone-Carving"], crafts=["Other-Stone-Carving"])
    lede[1] = dict(lede[1], subCategories=["Stone-Inlay"], crafts=["Mysuru-Stone-Carving"])
    question = {
        "id": "O01",
        "question": "No source was found on the other stone crafts of this category.",
        "subCategories": ["Stone-Others"],
    }
    defaults = {"scope": "CATEGORY", "categorySlug": STONE, "openQuestions": [question]}
    return plain | defaults | header


def category_messages(plain: dict[str, Any]) -> list[tuple[str, str]]:
    problems = content_problems(Dossier.model_validate(plain), default_context())
    return [(problem.where, problem.message) for problem in problems if problem.where != "coverage"]


def test_a_category_dossier_names_its_category_and_no_craft() -> None:
    dossier = Dossier.model_validate(category_plain())
    assert (dossier.scope, dossier.slug, dossier.craft_slug) == ("CATEGORY", STONE, None)
    with pytest.raises(ValidationError, match="names its categorySlug and no craftSlug"):
        Dossier.model_validate(category_plain(craftSlug="Kutch-Ajrakh"))
    with pytest.raises(ValidationError, match="names its categorySlug and no craftSlug"):
        Dossier.model_validate(category_plain(scope="CRAFT"))
    with pytest.raises(ValidationError, match="names the sub-categories no source was found for"):
        Dossier.model_validate(category_plain(openQuestions=[{"id": "O01", "question": "Is it known?"}]))


def test_a_category_that_covers_every_sub_category_passes() -> None:
    assert category_messages(category_plain()) == []


def test_the_category_slug_is_a_master_list_category() -> None:
    assert category_messages(category_plain(categorySlug="Glass-Craft-Category"))[0] == (
        "categorySlug",
        "Glass-Craft-Category is not a categorySlug of the master list",
    )


def test_every_sub_category_is_covered_by_a_sentence_or_an_open_question() -> None:
    plain = category_plain(openQuestions=[])
    lede = plain["overview"]["lede"]
    lede[1] = dict(lede[1], subCategories=[])
    assert category_messages(plain) == [
        ("overview", f"sub-category Stone-Inlay (Stone (Inlay)) {UNCOVERED}"),
        ("overview", f"sub-category Stone-Others (Stone (Others)) {UNCOVERED}"),
    ]


def test_sub_categories_and_member_crafts_belong_to_the_category() -> None:
    plain = category_plain()
    lede = plain["overview"]["lede"]
    lede[0] = dict(lede[0], subCategories=["Stone-Carving", "Hand-Block-Printing"], crafts=["Kutch-Ajrakh"])
    lede[1] = dict(lede[1], crafts=["Mysuru-Stone-Carving", "Cane-And-Bamboo", "Not-A-Craft"])
    assert category_messages(plain) == [
        ("overview.lede.0", f"Hand-Block-Printing is not a sub-category of {STONE}"),
        ("overview.lede.0", f"Kutch-Ajrakh is not a member craft of {STONE}"),
        ("overview.lede.1", f"Cane-And-Bamboo is not a member craft of {STONE}"),
        ("overview.lede.1", f"Not-A-Craft is not a member craft of {STONE}"),
    ]


def test_a_category_has_no_gi_record_and_a_section_for_each_supported_discipline() -> None:
    plain = category_plain(market={"gi": {"applicationNumber": "83", "claimIds": ["C001"]}})
    template = plain["claims"][0]
    plain["claims"] += [dict(template, id=f"C{n:03d}", discipline="DESIGN") for n in range(8, 11)]
    messages = category_messages(plain)
    assert ("market.gi", "a category has no GI record; a GI names one craft") in messages
    assert ("overview", "DESIGN has 3 claims and no section; the sources support one") in messages


def test_a_category_takes_up_to_250_claims_and_needs_no_process_stage() -> None:
    plain = category_plain(coverage="FULL")
    template = plain["claims"][0]
    plain["claims"] = [dict(template, id=f"C{n:03d}") for n in range(1, 252)]
    category = Dossier.model_validate(plain)
    assert coverage_problems(category)[0].message == "251 claims; a CATEGORY dossier holds at most 250"
    shortfalls = full_shortfalls(category.model_copy(update={"claims": category.claims[:60], "stages": []}))
    assert shortfalls[:2] == ["at least 12 sources (has 2)", "at least 5 sources rated A or B (has 1)"]
    assert "the process stages its sources name" not in shortfalls
    assert not [shortfall for shortfall in shortfalls if shortfall.startswith("at least 60 claims")]
    fewer = full_shortfalls(category.model_copy(update={"claims": category.claims[:59]}))
    assert "at least 60 claims (has 59)" in fewer
    craft = Dossier.model_validate(passing_plain() | {"claims": plain["claims"][:151]})
    assert coverage_problems(craft)[0].message == "151 claims; a CRAFT dossier holds at most 150"


def write(path: Path, plain: dict[str, Any]) -> Dossier:
    path.parent.mkdir(parents=True, exist_ok=True)
    dossier = Dossier.model_validate(plain)
    path.write_text(json.dumps(plain, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    check = path.with_name(f"{dossier.slug}.check.json")
    check.write_text(check_file_text(check_for(dossier)), encoding="utf-8", newline="\n")
    return dossier


def test_a_category_dossier_lives_in_the_categories_folder(tmp_path: Path) -> None:
    write(tmp_path / "categories" / f"{STONE}.json", category_plain())
    write(tmp_path / "Kutch-Ajrakh.json", passing_plain())
    assert [path.name for path in dossier_paths(tmp_path)] == ["Kutch-Ajrakh.json"]
    assert [path.name for path in category_paths(tmp_path)] == [f"{STONE}.json"]
    assert checked_dossier(tmp_path / "categories" / f"{STONE}.json", default_context()).problems == ()
    assert stray_problems(tmp_path) == []
    misplaced = write(tmp_path / f"{STONE}.json", category_plain())
    assert ("file", "a category dossier lives in categories/") in [
        (problem.where, problem.message)
        for problem in checked_dossier(tmp_path / f"{misplaced.slug}.json", default_context()).problems
    ]
    write(tmp_path / "categories" / "Kutch-Ajrakh.json", passing_plain())
    assert ("file", "a CRAFT dossier lives beside the others, not in categories/") in [
        (problem.where, problem.message)
        for problem in checked_dossier(
            tmp_path / "categories" / "Kutch-Ajrakh.json", default_context()
        ).problems
    ]
    (tmp_path / "categories" / "notes.txt").write_text("draft\n", encoding="utf-8")
    assert [(problem.where, problem.message) for problem in stray_problems(tmp_path)] == [
        ("categories/notes.txt", "is not a dossier, a check file or the index")
    ]


def test_a_category_check_file_names_its_category_and_a_craft_check_file_is_unchanged() -> None:
    category = Dossier.model_validate(category_plain())
    plain = json.loads(check_file_text(check_for(category)))
    assert (plain["categorySlug"], "craftSlug" in plain) == (STONE, False)
    craft = Dossier.model_validate(passing_plain())
    assert list(json.loads(check_file_text(check_for(craft))))[:3] == [
        "schemaVersion",
        "craftSlug",
        "dossierVersion",
    ]
    assert verified_digest(category) != verified_digest(
        Dossier.model_validate(passing_plain() | {"craftSlug": STONE})
    )
