from __future__ import annotations

import uuid

from app.services.curated_index import (
    CuratedPage,
    IndexAfter,
    IndexFocal,
    IndexNativeName,
    IndexPlacement,
)

from .import_support import AJRAKH, expected_id, plan_of

SINDHI = "اجرڪ"


def ajrakh_claim(key: str) -> uuid.UUID:
    return expected_id(f"curation:Kutch-Ajrakh:{key}")


def test_stage_after_and_why_carry_the_stored_claim_ids() -> None:
    stages = {stage.key: stage for stage in plan_of(AJRAKH).index.stages}
    assert stages["P05"].after == IndexAfter(
        text="Black outlines", colours=["BLACK"], claim_id=ajrakh_claim("C075")
    )
    assert stages["P11"].after == IndexAfter(
        text="Brighter, more brilliant red and blue", colours=["RED", "BLUE"], claim_id=ajrakh_claim("C091")
    )
    assert stages["P05"].why_claim_id == ajrakh_claim("C078")
    assert stages["P14"].why_claim_id == ajrakh_claim("C103")
    assert (stages["P04"].after, stages["P04"].why_claim_id) == (None, None)


def test_pictures_carry_placement_focal_size_and_stand_in() -> None:
    pictures = {picture.key: picture for picture in plan_of(AJRAKH).index.pictures}
    masthead = pictures["I02"]
    assert masthead.placement == IndexPlacement(chapter="glance", role="MASTHEAD")
    assert masthead.focal == IndexFocal(x=0.0, y=0.06, width=1.0, height=0.56)
    assert (masthead.width, masthead.height, masthead.stand_in) == (3264, 2448, None)
    block = pictures["I08"]
    assert block.placement == IndexPlacement(chapter="made", role="STAGE", stage_key="P14")
    assert (block.stage_key, block.claim_ids, block.stand_in) == (
        "P14",
        [],
        "A Jaipur block, not an ajrakh block",
    )
    madder = pictures["I06"]
    assert madder.placement == IndexPlacement(chapter="chem", role="MATERIAL", material_key="M19")
    assert (madder.width, madder.height) == (3264, 2448)
    assert [
        key for key, picture in pictures.items() if picture.placement and picture.placement.role == "OPENER"
    ] == ["I07"]


def test_native_names_carry_the_stored_claim_id() -> None:
    assert plan_of(AJRAKH).index.native_names == [
        IndexNativeName(text=SINDHI, language="sd", script="Arab", claim_id=ajrakh_claim("C152")),
        IndexNativeName(text="ajrak", language="sd", script="Latn", claim_id=ajrakh_claim("C152")),
    ]


def test_stored_media_rows_record_the_file_size() -> None:
    media = {row["imageUrl"]: row for row in plan_of(AJRAKH).part("media")}
    king = media["https://upload.wikimedia.org/wikipedia/commons/b/bd/KING_PRIEST.jpg"]
    assert (king["width"], king["height"], king["licence"]) == (1424, 2000, "CC BY-SA 4.0")
    vats = media[
        "https://upload.wikimedia.org/wikipedia/commons/a/a9/08-Indigo-factory-%28beating-the-Vats%29-bw.jpg"
    ]
    assert (vats["width"], vats["height"], vats["display"], vats["licence"]) == (
        4463,
        3832,
        "INLINE",
        "Public domain",
    )


def test_the_index_round_trips_and_a_version_1_row_without_the_new_fields_still_loads() -> None:
    index = plan_of(AJRAKH).index
    stored = index.model_dump(mode="json", by_alias=True)
    assert CuratedPage.model_validate(stored) == index
    assert stored["stages"][4]["after"] == {
        "text": "Black outlines",
        "colours": ["BLACK"],
        "claimId": str(ajrakh_claim("C075")),
    }
    for stage in stored["stages"]:
        stage.pop("after")
        stage.pop("whyClaimId")
    for picture in stored["pictures"]:
        for key in ("placement", "focal", "width", "height", "standIn"):
            picture.pop(key)
    stored.pop("nativeNames")
    older = CuratedPage.model_validate(stored)
    assert (older.native_names, older.stages[4].after, older.pictures[0].placement) == ([], None, None)
