from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from app.curation.checks import content_problems, default_context
from app.curation.dossier import Dossier
from app.curation.files import checked_dossier
from app.curation.limits import PICTURES_MAX
from app.curation.page_rules import (
    names_the_craft,
    native_name_problems,
    placement_problems,
    stage_page_problems,
    states_colour_word,
)

from .builders import PASSING, changed_dossier, passing_plain

SINDHI = "اجرڪ"
NAMED_QUOTE = "Ajrakh (also spelt ajrak in Sindh) is a resist printed cloth of Kachchh"
LABELLED_QUOTE = f"Ajrak (Sindhi: {SINDHI}) is a form of block printing found in Sindh"


def found(problems: list[Any]) -> list[tuple[str, str]]:
    return [(problem.where, problem.message) for problem in problems]


def picture(picture_id: str, **fields: Any) -> dict[str, Any]:
    return {
        "id": picture_id,
        "url": f"https://upload.wikimedia.org/wikipedia/commons/0/00/{picture_id}.jpg",
        "pageUrl": f"https://commons.wikimedia.org/wiki/File:{picture_id}.jpg",
        "author": "A photographer",
        "licence": "CC BY-SA 4.0",
        "caption": "An ajrakh held up to the light",
        "claimIds": ["C001"],
        **fields,
    }


def with_pictures(*pictures: dict[str, Any]) -> Callable[[dict[str, Any]], None]:
    def change(plain: dict[str, Any]) -> None:
        plain["pictures"] = list(pictures)

    return change


def with_stage(stage_id: str, **fields: Any) -> Callable[[dict[str, Any]], None]:
    def change(plain: dict[str, Any]) -> None:
        stage = next(stage for stage in plain["stages"] if stage["id"] == stage_id)
        stage.update(fields)

    return change


def named_claim(quote: str, subject: dict[str, str] | None = None) -> Callable[[dict[str, Any]], None]:
    def change(plain: dict[str, Any]) -> None:
        plain["claims"].append(
            {
                "id": "C010",
                "discipline": "OVERVIEW",
                "subject": subject or {"type": "CRAFT"},
                "text": "Ajrakh is also spelt ajrak in Sindh, where the cloth is printed.",
                "quotes": [{"sourceId": "S01", "locator": "para 9", "quote": quote}],
            }
        )

    return change


def both(*changes: Callable[[dict[str, Any]], None]) -> Callable[[dict[str, Any]], None]:
    def change(plain: dict[str, Any]) -> None:
        for each in changes:
            each(plain)

    return change


def test_a_schema_1_dossier_is_refused_with_the_migration_to_run() -> None:
    plain = passing_plain() | {"schemaVersion": 1}
    with pytest.raises(ValidationError) as refused:
        Dossier.model_validate(plain)
    assert "schemaVersion 1 is no longer read; run python tools/curation/migrate.py" in str(refused.value)


def test_the_passing_fixture_is_schema_2() -> None:
    assert passing_plain()["schemaVersion"] == 2


def test_a_schema_1_file_gets_one_line_naming_the_migration(tmp_path: Path) -> None:
    path = tmp_path / PASSING.name
    path.write_text(
        PASSING.read_text(encoding="utf-8").replace('"schemaVersion": 2', '"schemaVersion": 1', 1),
        encoding="utf-8",
        newline="\n",
    )
    result = checked_dossier(path, default_context())
    assert result.dossier is None
    assert found(list(result.problems)) == [
        (
            "dossier",
            "Value error, schemaVersion 1 is no longer read; run python tools/curation/migrate.py "
            "to rewrite the dossier as schema 2",
        )
    ]


@pytest.mark.parametrize(
    "change",
    [
        with_stage("P01", after={"text": "x" * 121, "claimId": "C003"}),
        with_stage("P01", after={"text": "Starch removed", "colours": ["TEAL"], "claimId": "C003"}),
        with_stage(
            "P01",
            after={"text": "Starch removed", "colours": ["RED", "BLUE", "BLACK", "WHITE"], "claimId": "C003"},
        ),
        with_stage("P01", after={"text": "Starch removed", "colours": ["RED", "RED"], "claimId": "C003"}),
        with_pictures(picture("I01", placement={"chapter": "atlas", "role": "PLATE"})),
        with_pictures(picture("I01", placement={"chapter": "made", "role": "STAGE"})),
        with_pictures(picture("I01", placement={"chapter": "made", "role": "PLATE", "stageId": "P01"})),
        with_pictures(picture("I01", placement={"chapter": "chem", "role": "MATERIAL"})),
        with_pictures(picture("I01", placement={"chapter": "chem", "role": "PLATE", "materialId": "M01"})),
        with_pictures(picture("I01", focal={"x": 0.5, "y": 0.0, "width": 0.6, "height": 1.0})),
        with_pictures(picture("I01", focal={"x": 0.0, "y": 0.0, "width": 0.0, "height": 1.0})),
        with_pictures(picture("I01", width=1200)),
        with_pictures(*(picture(f"I{number:02d}") for number in range(1, PICTURES_MAX + 2))),
        lambda plain: plain.update(nativeNames=[{"text": "ajrak", "language": "Sindhi", "claimId": "C001"}]),
    ],
)
def test_the_schema_refuses_new_fields_off_the_contract(change: Callable[[dict[str, Any]], None]) -> None:
    plain = passing_plain()
    change(plain)
    with pytest.raises(ValidationError):
        Dossier.model_validate(plain)


def test_sixteen_pictures_with_sizes_focal_boxes_and_placements_are_read() -> None:
    pictures = [picture(f"I{number:02d}", width=4000, height=3000) for number in range(1, PICTURES_MAX + 1)]
    pictures[0] |= {
        "placement": {"chapter": "glance", "role": "MASTHEAD"},
        "focal": {"x": 0.0, "y": 0.06, "width": 1.0, "height": 0.56},
        "standIn": "Tasar silk, not ajrakh",
    }
    dossier = changed_dossier(with_pictures(*pictures))
    first = dossier.pictures[0]
    assert len(dossier.pictures) == 16
    assert (first.width, first.height, first.stand_in) == (4000, 3000, "Tasar silk, not ajrakh")
    assert first.placement is not None and (first.placement.chapter, first.placement.role) == (
        "glance",
        "MASTHEAD",
    )
    assert first.focal is not None and (first.focal.y, first.focal.height) == (0.06, 0.56)


def test_an_after_rests_on_a_claim_of_its_stage_that_states_its_words() -> None:
    passing = changed_dossier(with_stage("P01", after={"text": "Starch removed", "claimId": "C003"}))
    assert stage_page_problems(passing) == []
    elsewhere = changed_dossier(with_stage("P01", after={"text": "Dried in the open sun", "claimId": "C007"}))
    assert found(stage_page_problems(elsewhere)) == [
        ("P01.after", "C007 is not a claim of P01; the after text rests on a fact claim of its stage")
    ]
    unstated = changed_dossier(with_stage("P02", after={"text": "Dried in the shade", "claimId": "C007"}))
    assert found(stage_page_problems(unstated)) == [
        ("P02.after", "shade in the after text is in neither C007's text nor its quotes")
    ]


def test_each_after_colour_is_named_by_a_quote_of_its_claim() -> None:
    def black_quote(plain: dict[str, Any]) -> None:
        plain["claims"][6]["quotes"][0]["quote"] = (
            "The printed cloth dried in the open sun turns a deep chocolate-black"
        )

    passing = changed_dossier(
        both(
            black_quote,
            with_stage(
                "P02", after={"text": "Dried in the open sun", "colours": ["BLACK"], "claimId": "C007"}
            ),
        )
    )
    assert stage_page_problems(passing) == []
    refused = changed_dossier(
        with_stage("P02", after={"text": "Dried in the open sun", "colours": ["WHITE"], "claimId": "C007"})
    )
    assert found(stage_page_problems(refused)) == [
        ("P02.after", "the colour WHITE is named in none of C007's quotes")
    ]


@pytest.mark.parametrize(
    ("text", "colour", "named"),
    [
        ("kut develops a deep fast chocolate-black colour", "BLACK", True),
        ("the cloth rapidly becomes blue", "BLUE", True),
        ("a gray cloth", "GREY", True),
        ("blue-black lines on the cloth", "BLUE", False),
        ("makes the whiteness of the stars shine", "WHITE", False),
        ("dyeing the purest reds", "RED", False),
    ],
)
def test_a_colour_is_its_word_or_the_last_word_of_a_compound(text: str, colour: str, named: bool) -> None:
    assert states_colour_word(text, colour) is named


def test_a_why_is_a_science_or_process_claim_about_the_stage_or_its_materials() -> None:
    of_stage = changed_dossier(with_stage("P01", whyClaimId="C003"))
    assert stage_page_problems(of_stage) == []
    of_material = changed_dossier(
        with_stage("P01", whyClaimId="C004", materials=[{"materialId": "M01", "claimId": "C003"}])
    )
    assert stage_page_problems(of_material) == []
    refused = changed_dossier(with_stage("P02", whyClaimId="C006"))
    assert found(stage_page_problems(refused)) == [
        (
            "P02.whyClaimId",
            "C006 is filed under ECONOMICS; a why is filed under CHEMISTRY, MATERIALS, PHYSICS, BOTANY or PROCESS",
        ),
        ("P02.whyClaimId", "C006 is about neither P02 nor one of its materials"),
    ]
    climate = changed_dossier(with_stage("P02", whyClaimId="C007"))
    assert found(stage_page_problems(climate)) == [
        (
            "P02.whyClaimId",
            "C007 is filed under CLIMATE; a why is filed under CHEMISTRY, MATERIALS, PHYSICS, BOTANY or PROCESS",
        )
    ]


def test_one_masthead_per_dossier_and_one_opener_per_chapter() -> None:
    passing = changed_dossier(
        with_pictures(
            picture("I01", placement={"chapter": "glance", "role": "MASTHEAD"}),
            picture("I02", placement={"chapter": "why", "role": "OPENER"}),
            picture("I03", placement={"chapter": "history", "role": "OPENER"}),
            picture("I04", placement={"chapter": "why", "role": "PLATE"}),
        )
    )
    assert placement_problems(passing) == []
    refused = changed_dossier(
        with_pictures(
            picture("I01", placement={"chapter": "glance", "role": "MASTHEAD"}),
            picture("I02", placement={"chapter": "people", "role": "MASTHEAD"}),
            picture("I03", placement={"chapter": "why", "role": "OPENER"}),
            picture("I04", placement={"chapter": "why", "role": "OPENER"}),
        )
    )
    assert found(placement_problems(refused)) == [
        ("pictures", "I01, I02 are all placed MASTHEAD; a dossier places one"),
        ("pictures", "I03, I04 are all placed OPENER in why; a chapter has one"),
    ]


def test_a_stage_placement_is_the_stage_the_picture_shows() -> None:
    passing = changed_dossier(
        with_pictures(
            picture("I01", stageId="P01", placement={"chapter": "made", "role": "STAGE", "stageId": "P01"})
        )
    )
    assert placement_problems(passing) == []
    refused = changed_dossier(
        with_pictures(
            picture("I01", stageId="P01", placement={"chapter": "made", "role": "STAGE", "stageId": "P02"})
        )
    )
    assert found(placement_problems(refused)) == [
        ("I01.placement", "is placed at stage P02 but shows stage P01")
    ]


def test_a_placement_names_a_stage_and_material_of_the_dossier() -> None:
    dossier = changed_dossier(
        with_pictures(
            picture("I01", placement={"chapter": "made", "role": "STAGE", "stageId": "P09"}),
            picture("I02", placement={"chapter": "chem", "role": "MATERIAL", "materialId": "M09"}),
        )
    )
    assert found(content_problems(dossier, default_context())) == [
        ("I01.placement", "P09 names no stage in the dossier"),
        ("I02.placement", "M09 names no material in the dossier"),
    ]


def test_a_native_name_occurs_in_a_quote_that_names_the_craft() -> None:
    spelt = changed_dossier(
        both(named_claim(NAMED_QUOTE), lambda plain: plain.update(nativeNames=[_name("ajrak", "Latn")]))
    )
    assert native_name_problems(spelt) == []
    labelled = changed_dossier(
        both(named_claim(LABELLED_QUOTE), lambda plain: plain.update(nativeNames=[_name(SINDHI, "Arab")]))
    )
    assert native_name_problems(labelled) == []
    absent = changed_dossier(
        both(named_claim(NAMED_QUOTE), lambda plain: plain.update(nativeNames=[_name("kachchhi", "Latn")]))
    )
    assert found(native_name_problems(absent)) == [
        ("nativeNames.0", "'kachchhi' occurs in none of C010's quotes")
    ]


def test_a_quote_merely_holding_the_word_does_not_name_the_craft() -> None:
    plain_mention = "Ajrak cloth is sold in the markets of Sindh to herders"
    dossier = changed_dossier(
        both(named_claim(plain_mention), lambda plain: plain.update(nativeNames=[_name("Ajrak", "Latn")]))
    )
    assert found(native_name_problems(dossier)) == [
        (
            "nativeNames.0",
            "no quote of C010 holding 'Ajrak' says the craft is called that "
            "(called, known as, named, spelt, or a language label before the name)",
        )
    ]
    about_a_place = changed_dossier(
        both(
            named_claim(NAMED_QUOTE, {"type": "PLACE", "ref": "L01"}),
            lambda plain: plain.update(nativeNames=[_name("ajrak", "Latn")]),
        )
    )
    assert found(native_name_problems(about_a_place)) == [
        ("nativeNames.0", "C010 is about a PLACE; a native name rests on a claim about the craft")
    ]


@pytest.mark.parametrize(
    ("quote", "name", "named"),
    [
        (LABELLED_QUOTE, SINDHI, True),
        ("The cloth known as ajrak is printed in Sindh", "ajrak", True),
        (f"Ajrak and {SINDHI} cloths are sold in Sindh", SINDHI, False),
    ],
)
def test_naming_words_or_a_language_label_name_the_craft(quote: str, name: str, named: bool) -> None:
    assert names_the_craft(quote, name) is named


def _name(text: str, script: str) -> dict[str, str]:
    return {"text": text, "language": "sd", "script": script, "claimId": "C010"}
