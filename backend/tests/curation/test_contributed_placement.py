from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, replace
from typing import Any

import pytest
from pydantic import ValidationError

from app.research.craft_contributed import ContributedPlate
from app.research.craft_page import CraftPage
from app.services.chapter_preview import preview_rows
from app.services.contributed_pictures import ContributedRecord
from app.services.craft_page import craft_page
from app.services.curation_preview import dossier_records

from ..contracts.golden import golden_json
from .import_support import AJRAKH, AJRAKH_GOLDEN

FAMILY = "Textiles-Based-Craft-Category"
UNKNOWN = uuid.UUID("5c0e0000-0000-4000-8000-0000000000ff")
TOOL = "ChatGPT (GPT-4o)"
CHAPTER_OF_FIELD = {"HISTORY": "history", "CHEMISTRY": "chem", "ECONOMICS": "market"}


def picture(n: int) -> uuid.UUID:
    return uuid.UUID(f"5c0e0000-0000-4000-8000-{n:012d}")


def listed_fact(field: str, nth: int = 0) -> uuid.UUID:
    claims = [c for c in golden_json(AJRAKH_GOLDEN)["claims"] if c["discipline"] == field]
    facts = [c for c in claims if c["level"] != "HYPOTHESIS" and c["provenance"] == "CURATED"]
    return uuid.UUID(facts[nth]["id"])


def first_stage() -> uuid.UUID:
    for chapter in golden_json(AJRAKH_GOLDEN)["chapters"]:
        for item in chapter["items"]:
            if (item["block"] or {}).get("kind") == "process_ladder":
                return uuid.UUID(item["block"]["stages"][0]["stageId"])
    raise AssertionError("the golden has no ladder")


def record(n: int, origin: str, claims: tuple[uuid.UUID, ...], **changes: Any) -> ContributedRecord:
    values: dict[str, Any] = {
        "contribution_id": picture(n),
        "origin": origin,
        "generator": TOOL if origin == "AI_GENERATED" else None,
        "caption": f"Contributed picture number {n}",
        "alt_text": f"What contributed picture number {n} shows",
        "stage_id": None,
        "claim_ids": claims,
        "mime": "image/jpeg",
        "width": 1200,
        "height": 800,
    }
    return ContributedRecord(**(values | changes))


@dataclass(frozen=True)
class Placed:
    chapter: str
    index: int
    plate: ContributedPlate


def placed_pictures(page: CraftPage) -> dict[uuid.UUID, Placed]:
    found = {}
    for chapter in page.chapters:
        for index, item in enumerate(chapter.items):
            if item.kind == "contributed":
                for plate in item.part.pictures:
                    found[plate.contribution_id] = Placed(chapter.key, index, plate)
    return found


def built(*records: ContributedRecord) -> CraftPage:
    stored = replace(dossier_records(AJRAKH), contributed=records)
    return craft_page(stored, preview_rows(stored, family=FAMILY, inputs=None))


@pytest.fixture(scope="module")
def page() -> CraftPage:
    history, chemistry, economics = listed_fact("HISTORY"), listed_fact("CHEMISTRY"), listed_fact("ECONOMICS")
    return built(
        record(1, "PHOTOGRAPH", (), stage_id=first_stage()),
        record(2, "AI_GENERATED", (history,), mime="image/png"),
        record(3, "DRAWING", (listed_fact("HISTORY", 1), chemistry, listed_fact("CHEMISTRY", 1))),
        record(4, "PHOTOGRAPH", (listed_fact("HISTORY", 2), listed_fact("CHEMISTRY", 2))),
        record(5, "PHOTOGRAPH", ()),
        record(6, "AI_GENERATED", (history, UNKNOWN)),
        record(7, "PHOTOGRAPH", (UNKNOWN, economics)),
    )


def test_a_stage_s_picture_is_in_the_made_chapter_right_after_the_ladder_at_its_stage(
    page: CraftPage,
) -> None:
    shown = placed_pictures(page)[picture(1)]
    (made,) = [chapter for chapter in page.chapters if chapter.key == "made"]
    assert shown.chapter == "made"
    assert made.items[shown.index - 1].kind == "process_ladder"
    assert shown.plate.stage_id == first_stage()
    assert shown.plate.stage_id in {stage.stage_id for stage in made.items[shown.index - 1].block.stages}


def test_a_picture_for_facts_is_in_the_chapter_of_their_field(page: CraftPage) -> None:
    shown = placed_pictures(page)
    assert shown[picture(2)].chapter == CHAPTER_OF_FIELD["HISTORY"]
    assert shown[picture(3)].chapter == CHAPTER_OF_FIELD["CHEMISTRY"]
    assert shown[picture(4)].chapter == "chem"
    assert shown[picture(7)].chapter == CHAPTER_OF_FIELD["ECONOMICS"]


def test_a_picture_of_no_stage_or_fact_is_at_a_glance(page: CraftPage) -> None:
    assert placed_pictures(page)[picture(5)].chapter == "glance"


def test_an_ai_image_whose_facts_are_not_all_on_the_page_is_not_shown(page: CraftPage) -> None:
    assert picture(6) not in placed_pictures(page)


def test_each_plate_is_credited_without_a_name_and_an_ai_image_as_an_illustration(page: CraftPage) -> None:
    shown = placed_pictures(page)
    assert {n: shown[picture(n)].plate.credit for n in (1, 3, 4, 5, 7)} == dict.fromkeys(
        (1, 3, 4, 5, 7), "Contributed to KalaVigyan"
    )
    assert shown[picture(2)].plate.credit == "Illustration, made with ChatGPT (GPT-4o)"
    assert shown[picture(2)].plate.made_with == TOOL
    assert shown[picture(2)].plate.url == f"/api/crafts/contributed/{picture(2)}"
    body = json.dumps(page.model_dump(mode="json", by_alias=True))
    assert "contributor" not in body.lower()


def test_a_plate_shows_its_caption_alt_text_and_only_listed_facts(page: CraftPage) -> None:
    shown = placed_pictures(page)[picture(7)].plate
    assert (shown.caption, shown.alt_text) == (
        "Contributed picture number 7",
        "What contributed picture number 7 shows",
    )
    cited = {citation.claim_id for sentence in shown.sentences for citation in sentence.citations}
    assert str(UNKNOWN) not in cited
    assert cited <= {str(listed_fact("ECONOMICS"))}


def test_a_chapter_shelves_at_most_six_pictures_in_approval_order() -> None:
    eight = built(*(record(n, "PHOTOGRAPH", ()) for n in range(10, 18)))
    (glance,) = [chapter for chapter in eight.chapters if chapter.key == "glance"]
    (shelf,) = [item.part for item in glance.items if item.kind == "contributed"]
    assert [plate.contribution_id for plate in shelf.pictures] == [picture(n) for n in range(10, 16)]


def test_no_contributed_picture_leaves_the_page_without_a_shelf() -> None:
    bare = built()
    assert placed_pictures(bare) == {}
    assert all(item.kind != "contributed" for chapter in bare.chapters for item in chapter.items)


def test_the_page_refuses_one_picture_shown_in_two_chapters(page: CraftPage) -> None:
    body = page.model_dump(mode="json", by_alias=True)
    (shelf,) = [
        item
        for chapter in body["chapters"]
        if chapter["key"] == "glance"
        for item in chapter["items"]
        if (item["part"] or {}).get("kind") == "contributed"
    ]
    history = next(chapter for chapter in body["chapters"] if chapter["key"] == "history")
    history["items"].append(shelf)
    with pytest.raises(ValidationError, match="each contributed picture once"):
        CraftPage.model_validate(body)
