import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.data.map_layers import LAYERS_DIR, WATERS_NAMES_FILE, held_dam_names, held_river_names
from app.research.component_specs_map_parts import DAMS_EMPHASISED_MAX, MapEmphasis
from app.research.component_specs_science_coded import MAP_WATERS_MAX, CodedMap
from app.services.map_layer_places import DAM_UNHELD, RIVER_UNHELD, held_water_problems

CONTRACTS = Path(__file__).resolve().parents[3] / "docs" / "contracts"
SURAN = "Suran"
DHAMADKA = "Dhamadka"
TAPPAR = "Tappar Reservoir"
AMANISHA = "Amanisha River"


def test_a_small_river_is_held_by_the_dataset_s_name_and_the_register_s_where_they_agree() -> None:
    rivers = held_river_names()
    assert {SURAN, DHAMADKA, AMANISHA, "Chambal"} <= rivers
    assert "Dravyavati" not in rivers
    assert "Brahmaputra Creek of Nowhere" not in rivers


def test_a_dam_is_held_by_the_name_openstreetmap_gives_it_or_its_reservoir() -> None:
    assert TAPPAR in held_dam_names()
    assert "Tapar Dam" not in held_dam_names()


def test_a_named_small_river_or_dam_is_allowed_and_an_unknown_one_is_refused_by_name() -> None:
    assert held_water_problems([SURAN, AMANISHA], [TAPPAR]) == []
    assert held_water_problems(["Dravyavati"], ["Tapar Dam"]) == [
        RIVER_UNHELD.format(name="Dravyavati"),
        DAM_UNHELD.format(name="Tapar Dam"),
    ]


def test_an_emphasis_may_name_dams_alone_each_once_and_an_old_one_is_stored_unchanged() -> None:
    assert MapEmphasis.model_validate({"dams": [TAPPAR]}).dams == [TAPPAR]
    with pytest.raises(ValidationError, match="each layer, river and dam once"):
        MapEmphasis.model_validate({"dams": [TAPPAR, TAPPAR]})
    with pytest.raises(ValidationError):
        MapEmphasis.model_validate({"dams": [f"Dam {at}" for at in range(DAMS_EMPHASISED_MAX + 1)]})
    with pytest.raises(ValidationError, match="names a layer, a river or a dam"):
        MapEmphasis.model_validate({})
    old = {"layers": ["rivers"], "rivers": ["Chambal"]}
    assert MapEmphasis.model_validate(old).model_dump(mode="json") == old


def test_a_coded_map_names_rivers_and_dams_and_an_old_one_is_stored_unchanged() -> None:
    named = CodedMap.model_validate(
        {"layers": ["rivers"], "districts": [449], "rivers": [SURAN], "dams": [TAPPAR]}
    )
    assert (named.rivers, named.dams) == ([SURAN], [TAPPAR])
    old = {"layers": ["states"], "districts": [449]}
    assert CodedMap.model_validate(old).model_dump(mode="json") == old


def test_the_contracts_state_how_a_river_or_dam_is_named() -> None:
    general = " ".join((CONTRACTS / "component-specs-general.md").read_text(encoding="utf-8").split())
    assert f"`dams` names up to {DAMS_EMPHASISED_MAX} dams" in general
    assert '"Dhamadka River (Suran)"' in general
    science = " ".join((CONTRACTS / "component-specs-science.md").read_text(encoding="utf-8").split())
    assert f"up to {MAP_WATERS_MAX} rivers and {MAP_WATERS_MAX} dams" in science
    assert "`kvMap.rivers`" in science and "`kvMap.dams`" in science


def test_the_api_reads_the_names_file_of_the_build_the_map_draws() -> None:
    body = json.loads((LAYERS_DIR / WATERS_NAMES_FILE).read_text(encoding="utf-8"))
    assert body["datasets"][0]["code"] == "OSM_WATERWAYS"
    assert body["rivers"] == sorted(body["rivers"]) and body["dams"] == sorted(body["dams"])
    assert set(body["rivers"]) <= held_river_names() and set(body["dams"]) == held_dam_names()
