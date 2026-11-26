from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from app.data.district_register import load_district_codes

from maplayers.waters_register import RegisterRiver, accepted_names, dossier_rivers, register_of

REPO_ROOT = Path(__file__).resolve().parents[2]
LAYERS = REPO_ROOT / "frontend" / "public" / "layers"
TILES = LAYERS / "waters"
NAMES = REPO_ROOT / "backend" / "app" / "data" / "layers" / "waters-names.json"
MODULE = REPO_ROOT / "frontend" / "lib" / "server" / "watersTiles.ts"
CURATION = REPO_ROOT / "backend" / "app" / "data" / "curation"
KACHCHH = 449
JAIPUR = 102
TAPAR = (70.13, 23.25)
TAPAR_REACH = 0.05
TILE_BYTES_MOST = 1_500_000
LAYER_BYTES_MOST = 12_000_000


def _json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _tiles() -> dict[str, Any]:
    return {path.stem: _json(path) for path in sorted(TILES.glob("*.json"))}


def _dossiers() -> list[RegisterRiver]:
    paths = [path for path in sorted(CURATION.glob("*.json")) if not path.name.endswith(".check.json")]
    return dossier_rivers(paths, load_district_codes())


def test_the_register_holds_the_dossiers_rivers_by_their_named_district() -> None:
    held = {(river.name, river.source): river.districts for river in _dossiers()}
    assert held[("Dhamadka River (Suran)", "Kutch-Ajrakh")] == frozenset({KACHCHH})
    assert held[("Amanishah Nala (Dravyavati river)", "Sanganeri-Hand-Block-Printing")] == frozenset({JAIPUR})


def test_a_river_agrees_with_the_register_only_by_a_shared_name_in_a_shared_district() -> None:
    register = register_of(_dossiers())
    agreed = register.agreeing("Dhamadka", [KACHCHH])
    assert [river.name for river in agreed] == ["Dhamadka River (Suran)"]
    assert "Suran" in accepted_names("Dhamadka", agreed)
    assert register.agreeing("Dhamadka", [JAIPUR]) == []
    assert register.agreeing("Amanisha River", [JAIPUR]) == []
    assert "Dravyavati" not in accepted_names("Amanisha River", register.agreeing("Amanisha River", [JAIPUR]))


def test_the_index_the_tiles_the_server_module_and_the_api_names_are_one_build() -> None:
    index = _json(LAYERS / "waters.json")
    tiles = _tiles()
    assert [tile["id"] for tile in index["tiles"]] == list(tiles)
    for row in index["tiles"]:
        assert (row["rivers"], row["dams"]) == (
            len(tiles[row["id"]]["rivers"]),
            len(tiles[row["id"]]["dams"]),
        )
    assert re.findall(r"^  (e\d{3}n\d{2}): ", MODULE.read_text(encoding="utf-8"), re.MULTILINE) == list(tiles)
    names = _json(NAMES)
    rivers = {
        name
        for tile in tiles.values()
        for row in tile["rivers"]
        for name in (row["name"], *row.get("also", []))
    }
    assert names["rivers"] == sorted(rivers)
    assert names["dams"] == sorted({row["name"] for tile in tiles.values() for row in tile["dams"]})
    assert names["datasets"] == index["datasets"] and index["datasets"][0]["code"] == "OSM_WATERWAYS"


def test_the_tiles_keep_to_the_repository_and_phone_budget() -> None:
    sizes = [path.stat().st_size for path in TILES.glob("*.json")]
    assert sizes and max(sizes) <= TILE_BYTES_MOST
    assert sum(sizes) <= LAYER_BYTES_MOST


def test_the_suran_below_the_dam_at_tapar_is_held_in_kachchh() -> None:
    rows = [row for tile in _tiles().values() for row in tile["rivers"] if KACHCHH in row["districts"]]
    suran = [row for row in rows if "Suran" in row.get("also", [])]
    assert suran and all(row["name"] == "Dhamadka" for row in suran)
    assert {"name": "Dhamadka River (Suran)", "source": "Kutch-Ajrakh"} in suran[0]["agrees"]
    dams = [row for tile in _tiles().values() for row in tile["dams"] if KACHCHH in row["districts"]]
    near = [
        dam
        for dam in dams
        if abs(dam["longitude"] - TAPAR[0]) <= TAPAR_REACH and abs(dam["latitude"] - TAPAR[1]) <= TAPAR_REACH
    ]
    assert [dam["name"] for dam in near] == ["Tappar Reservoir"]
    assert near[0]["namedBy"] == "reservoir"


def test_the_dravyavati_is_held_in_jaipur_under_the_name_the_dataset_gives_it() -> None:
    rows = [row for row in _tiles()["e074n26"]["rivers"] if JAIPUR in row["districts"]]
    assert "Amanisha River" in {row["name"] for row in rows}
