import json
from typing import Any

import pytest

from app.data.craft_families import (
    CRAFT_FAMILIES_FILE,
    FAMILY_PALETTES,
    load_craft_families,
    parse_craft_families,
)
from app.data.craft_master_loader import load_master
from app.data.craft_names import CRAFT_NAMES_FILE, load_craft_names, parse_craft_names
from app.data.district_register import load_district_register
from app.data.state_languages import STATE_LANGUAGES_FILE, load_state_languages, parse_state_languages


def _raw(path: Any) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def test_every_family_has_its_own_palette_from_the_listed_keys() -> None:
    families = load_craft_families().families
    assert [family.palette for family in families] == list(FAMILY_PALETTES)
    raw = _raw(CRAFT_FAMILIES_FILE)
    raw["families"][1]["palette"] = "purple"
    with pytest.raises(ValueError, match="purple"):
        parse_craft_families(raw, load_master())
    raw["families"][1]["palette"] = raw["families"][0]["palette"]
    with pytest.raises(ValueError, match="palette"):
        parse_craft_families(raw, load_master())


def test_display_names_correct_master_spellings_without_renaming_the_record() -> None:
    names = load_craft_names()
    assert names.display_name("Metal-Embosing", "Metal Embosing") == "Metal Embossing"
    assert names.display_name("Immitation-Jewellery", "Immitation Jewellery") == "Imitation Jewellery"
    assert names.display_name("Kutch-Ajrakh", "Kutch Ajrakh") == "Kutch Ajrakh"
    assert names.sets_local_name("Assam-Majuli-Manuscript-Painting")
    assert names.local_name("Assam-Majuli-Manuscript-Painting") is None
    assert not names.sets_local_name("Phulkari")


@pytest.mark.parametrize(
    ("crafts", "problem"),
    [
        ({"No-Such-Craft": {"displayName": "Anything"}}, "not a master craft"),
        ({"Kutch-Ajrakh": {"nickname": "Ajrak"}}, "unknown field"),
        ({"Kutch-Ajrakh": {"displayName": "Kutch Ajrakh"}}, "repeats its master name"),
        ({"Other-Hand-Block-Print": {"displayName": "More prints"}}, "catch-all"),
        ({"Kutch-Ajrakh": {"displayName": " Ajrakh"}}, "outer spaces"),
    ],
)
def test_a_bad_craft_name_edit_is_refused(crafts: dict[str, Any], problem: str) -> None:
    with pytest.raises(ValueError, match=problem):
        parse_craft_names({"schemaVersion": 1, "crafts": crafts}, load_master())


def test_the_craft_names_file_is_versioned() -> None:
    raw = _raw(CRAFT_NAMES_FILE)
    raw["schemaVersion"] = 2
    with pytest.raises(ValueError, match="schemaVersion"):
        parse_craft_names(raw, load_master())


def test_every_state_of_india_names_its_languages() -> None:
    languages = load_state_languages()
    assert set(languages) == set(load_district_register().states)
    assert languages["Punjab"] == ("pa",)
    assert languages["Karnataka"] == ("kn",)
    assert languages["Nagaland"] == ()


@pytest.mark.parametrize(
    ("change", "problem"),
    [
        (lambda states: states.pop("Punjab"), "Punjab"),
        (lambda states: states.update({"Atlantis": []}), "Atlantis"),
        (lambda states: states.update({"Punjab": ["Punjabi"]}), "ISO 639"),
        (lambda states: states.update({"Punjab": ["pa", "pa"]}), "ISO 639"),
    ],
)
def test_a_bad_state_language_list_is_refused(change: Any, problem: str) -> None:
    raw = _raw(STATE_LANGUAGES_FILE)
    change(raw["states"])
    with pytest.raises(ValueError, match=problem):
        parse_state_languages(raw, load_district_register().states)
