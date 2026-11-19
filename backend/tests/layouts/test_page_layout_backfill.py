import pytest

from app.services.page_layouts_backfill import picture_entries, picture_placement

from .pictures import picture

FOCAL = {"x": 0.1, "y": 0.25, "width": 0.8, "height": 0.5}


@pytest.mark.parametrize(
    ("built", "expected"),
    [
        (picture("I01", role="MASTHEAD", chapter="made"), ("glance", "HERO")),
        (picture("I02", role="OPENER", chapter="chem"), ("chem", "OPENER")),
        (picture("I03", role="PLATE", chapter="history"), ("history", "PLATE")),
        (picture("I04", role="MATERIAL", chapter="chem", placed={"materialKey": "M01"}), ("chem", "PLATE")),
        (picture("I05", role="RECORD", chapter="market"), ("market", "FIGURE")),
        (picture("I06", role="STAGE", chapter="made", placed={"stageKey": "P02"}), ("made", "FIGURE")),
        (picture("I07", stage_key="P03"), ("made", "FIGURE")),
        (picture("I08"), ("glance", "PLATE")),
    ],
)
def test_a_dossier_placement_becomes_a_chapter_and_a_layout_role(
    built: object, expected: tuple[str, str]
) -> None:
    assert picture_placement(built) == expected


def test_the_backfill_leads_each_chapter_with_its_hero_or_opener_and_keeps_the_crops() -> None:
    pictures = [
        picture("I01", role="PLATE", chapter="glance"),
        picture("I02", role="MASTHEAD", chapter="glance", focal=FOCAL),
        picture("I03", role="MATERIAL", chapter="chem", placed={"materialKey": "M01"}),
        picture("I04", role="OPENER", chapter="chem"),
    ]
    found = [
        (e.ref, e.chapter, e.order, e.role, e.crop.model_dump() if e.crop else None, e.size, e.caption)
        for e in picture_entries("Bagh-Print", pictures)
    ]
    assert found == [
        ("bagh-print/pictures/i02", "glance", 1, "HERO", FOCAL, None, None),
        ("bagh-print/pictures/i04", "chem", 1, "OPENER", None, None, None),
        ("bagh-print/pictures/i01", "glance", 2, "PLATE", None, None, None),
        ("bagh-print/pictures/i03", "chem", 2, "PLATE", None, None, None),
    ]


def test_a_craft_without_pictures_backfills_no_entries() -> None:
    assert picture_entries("Bagh-Print", []) == []
