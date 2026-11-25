import json
from pathlib import Path

from app.research.art_kit import FAMILIES, KIT_PARTS, kit_vocabulary, parts_named_by
from app.research.depicted_materials import DEPICTED_MATERIALS

GOLDEN = Path(__file__).resolve().parents[3] / "shared" / "art-kit.golden.json"
NINE_FAMILIES = ("textiles", "metal", "clay", "stone", "wood", "leather", "fibre", "paper", "more")
PARTS_PER_FAMILY = {
    "textiles": 9,
    "metal": 8,
    "clay": 4,
    "stone": 3,
    "wood": 5,
    "leather": 4,
    "fibre": 6,
    "paper": 7,
    "more": 7,
}


def test_the_kit_s_vocabulary_is_the_shared_golden_both_sides_read() -> None:
    assert kit_vocabulary() == json.loads(GOLDEN.read_text(encoding="utf-8"))


def test_the_kit_holds_the_parts_kutch_ajrakh_s_figures_are_made_of() -> None:
    assert list(KIT_PARTS) == [
        "cloth",
        "block",
        "bath",
        "paste",
        "heat",
        "water",
        "tool",
        "section",
        "piece",
        "species",
    ]
    assert KIT_PARTS["cloth"].choices["form"] == ("swatch", "length", "folded")
    assert "sun" in KIT_PARTS["heat"].choices["source"]
    assert "block" in KIT_PARTS["tool"].choices["tool"]
    assert KIT_PARTS["section"].materials == ("layers.material",)
    assert kit_vocabulary()["earth"] == "earth"


def test_every_family_of_the_atlas_is_served_by_two_parts_or_more() -> None:
    assert FAMILIES == NINE_FAMILIES
    counted = {family: sum(family in part.families for part in KIT_PARTS.values()) for family in FAMILIES}
    assert counted == PARTS_PER_FAMILY
    assert all(set(part.families) <= set(FAMILIES) and part.families for part in KIT_PARTS.values())


def test_the_parts_that_take_a_material_name_where_and_the_motions_explain_one_part_each() -> None:
    takers = [name for name, part in KIT_PARTS.items() if part.materials]
    assert takers == ["cloth", "block", "bath", "paste", "tool", "section", "piece", "species"]
    moving = {name: part.motion for name, part in KIT_PARTS.items() if part.motion}
    assert moving == {"cloth": "take", "bath": "dip", "paste": "dry", "species": "react"}
    assert len(DEPICTED_MATERIALS) == 34


def test_words_name_the_kit_parts_they_show_once_each_in_the_order_said() -> None:
    assert parts_named_by("A cotton swatch dipped in the vat, then the cloth in the sun") == [
        ("cloth", "cotton"),
        ("bath", "vat"),
        ("heat", "sun"),
    ]
    assert parts_named_by("The Punjab turner's lathe and its bow") == []
    assert parts_named_by("Depth drawn to scale: WATER once rose") == [("water", "water")]


def test_a_reaction_s_species_is_a_part_every_family_draws_in_its_role() -> None:
    species = KIT_PARTS["species"]
    assert species.families == FAMILIES
    assert species.choices["role"] == ("reactant", "reagent", "product")
    assert species.materials == ("material",)
    assert kit_vocabulary()["speciesPerSceneMax"] == 8
    assert kit_vocabulary()["partsPerPanelMax"] == 3
    assert parts_named_by("Oxygen, the reagent, arrives") == [("species", "reagent")]
    assert parts_named_by("Oxygen arrives from the air") == []
