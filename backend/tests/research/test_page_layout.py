from typing import Any

import pytest
from pydantic import ValidationError

from app.core.errors import InvalidInput
from app.research.monograph_page import LayoutEntry
from app.research.page_layout import LayoutWrite, PageLayout, PageLayoutEntry, arranged_layout, picture_label

PHOTO = "bagh-print/pictures/i01"
PLAYER = "shared/chemistry/indigo-reduction-player"


def entry(ref: str, chapter: str, order: int, role: str, **extra: Any) -> dict[str, Any]:
    return {"ref": ref, "chapter": chapter, "order": order, "role": role, **extra}


def layout(*entries: dict[str, Any]) -> PageLayout:
    return PageLayout.model_validate(
        {"subjectKind": "craft", "subjectSlug": "Bagh-Print", "version": 1, "entries": list(entries)}
    )


def test_an_entry_names_a_unit_by_id_or_a_component_by_label() -> None:
    assert PageLayoutEntry.model_validate(entry("chemistry-3f2a", "chem", 1, "BODY")).ref == "chemistry-3f2a"
    crop = {"x": 0.1, "y": 0.2, "width": 0.5, "height": 0.6}
    plate = PageLayoutEntry.model_validate(entry(PHOTO, "glance", 1, "PLATE", crop=crop, caption="A cloth"))
    assert (plate.crop.x, plate.crop.height, plate.caption) == (0.1, 0.6, "A cloth")
    with pytest.raises(ValidationError, match="neither a unit id nor a component label"):
        PageLayoutEntry.model_validate(entry("Bagh/Print photo", "glance", 1, "PLATE"))


@pytest.mark.parametrize(
    ("ref", "role", "extra", "problem"),
    [
        (PHOTO, "PULL_QUOTE", {}, "a PULL_QUOTE is a text unit"),
        ("u0001", "HERO", {}, "a HERO is a component"),
        ("u0001", "OPENER", {}, "a OPENER is a component"),
        (
            "u0001",
            "BODY",
            {"crop": {"x": 0, "y": 0, "width": 1, "height": 1}},
            "only a component takes a crop",
        ),
        ("u0001", "SIDEBAR", {"caption": "Over"}, "only a component takes a crop or a caption"),
    ],
)
def test_roles_crops_and_captions_fit_what_they_place(ref: str, role: str, extra: dict, problem: str) -> None:
    with pytest.raises(ValidationError, match=problem):
        PageLayoutEntry.model_validate(entry(ref, "glance", 1, role, **extra))


def test_a_crop_outside_its_picture_or_an_unknown_size_is_refused() -> None:
    with pytest.raises(ValidationError, match="inside its picture"):
        PageLayoutEntry.model_validate(
            entry(PHOTO, "glance", 1, "PLATE", crop={"x": 0.6, "y": 0, "width": 0.5, "height": 1})
        )
    with pytest.raises(ValidationError):
        PageLayoutEntry.model_validate(entry(PHOTO, "glance", 1, "PLATE", size="HUGE"))
    assert PageLayoutEntry.model_validate(entry(PHOTO, "glance", 1, "PLATE", size="BLEED")).size == "BLEED"


@pytest.mark.parametrize(
    ("entries", "problem"),
    [
        (
            [entry("u1", "chem", 1, "BODY"), entry("u1", "made", 1, "BODY")],
            "places each unit or component once",
        ),
        (
            [entry("u1", "chem", 2, "BODY"), entry("u2", "chem", 2, "BODY")],
            "share a place in their chapter: \\['chem 2'\\]",
        ),
        ([entry(PHOTO, "glance", 1, "HERO"), entry(PLAYER, "chem", 1, "HERO")], "a page has one HERO"),
        (
            [entry(PHOTO, "chem", 1, "OPENER"), entry(PLAYER, "chem", 2, "OPENER")],
            "a chapter has one OPENER: \\['chem'\\]",
        ),
    ],
)
def test_a_layout_places_each_ref_once_one_per_slot_one_hero_one_opener_a_chapter(
    entries: list[dict[str, Any]], problem: str
) -> None:
    with pytest.raises(ValidationError, match=problem):
        layout(*entries)
    with pytest.raises(ValidationError, match=problem):
        LayoutWrite.model_validate({"baseVersion": 0, "entries": entries})


def test_openers_in_two_chapters_and_the_same_order_in_two_chapters_are_allowed() -> None:
    found = layout(entry(PHOTO, "chem", 1, "OPENER"), entry(PLAYER, "made", 1, "OPENER"))
    assert [e.chapter for e in found.entries] == ["chem", "made"]


def test_a_write_names_the_version_it_builds_on() -> None:
    assert LayoutWrite.model_validate({"baseVersion": 3, "entries": []}).base_version == 3
    with pytest.raises(ValidationError):
        LayoutWrite.model_validate({"baseVersion": -1, "entries": []})


def test_a_picture_label_is_the_slug_the_pictures_segment_and_the_dossier_key() -> None:
    assert picture_label("Bagh-Print", "I01") == "bagh-print/pictures/i01"
    with pytest.raises(InvalidInput, match="no component label"):
        picture_label("Bagh--Print", "I01")


def unit(chapter: str, ref: str, within: str | None = None) -> LayoutEntry:
    return LayoutEntry(chapter=chapter, kind="unit", ref=ref, within=within)


def component(chapter: str, ref: str) -> LayoutEntry:
    return LayoutEntry(chapter=chapter, kind="component", ref=ref)


DEFAULT = [
    unit("glance", "a"),
    component("glance", PHOTO),
    unit("glance", "a1", within=PHOTO),
    unit("made", "b"),
    unit("made", "c"),
    component("made", PLAYER),
]


def placed(entries: list[LayoutEntry]) -> list[tuple[str, str, str | None]]:
    return [(e.chapter, e.ref, e.within) for e in entries]


def test_without_a_layout_the_default_order_stands_in_chapter_order() -> None:
    assert placed(arranged_layout(list(reversed(DEFAULT[3:])) + DEFAULT[:3], None)) == [
        ("glance", "a", None),
        ("glance", PHOTO, None),
        ("glance", "a1", PHOTO),
        ("made", PLAYER, None),
        ("made", "c", None),
        ("made", "b", None),
    ]


def test_named_entries_lead_their_chapter_in_order_and_carry_what_sits_within_them() -> None:
    chosen = layout(
        entry(PLAYER, "made", 1, "FIGURE"),
        entry("c", "glance", 2, "BODY"),
        entry(PHOTO, "glance", 1, "HERO"),
        entry("gone", "chem", 1, "BODY"),
    )
    assert placed(arranged_layout(DEFAULT, chosen)) == [
        ("glance", PHOTO, None),
        ("glance", "a1", PHOTO),
        ("glance", "c", None),
        ("glance", "a", None),
        ("made", PLAYER, None),
        ("made", "b", None),
    ]


def test_a_chapter_the_template_does_not_know_follows_the_known_ones() -> None:
    chosen = layout(entry("a", "reading", 1, "BODY"))
    assert [e.chapter for e in arranged_layout(DEFAULT, chosen)] == ["glance"] * 2 + ["made"] * 3 + [
        "reading"
    ]


def test_an_entry_within_a_component_the_page_lacks_is_refused() -> None:
    with pytest.raises(InvalidInput, match="components the page lacks"):
        arranged_layout([unit("glance", "a", within=PLAYER)], None)
