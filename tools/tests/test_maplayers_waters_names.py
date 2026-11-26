from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from maplayers.layer_files import layer_text
from maplayers.waters_names import WATERS_NAMES, WATERS_TILES, registered_waters, reregister_files
from maplayers.waters_register import RegisterRiver, accepted_names, register_of

JAIPUR = 102
KACHCHH = 449
DATASET = {"code": "OSM_WATERWAYS", "readOn": "2026-11-26"}
ALIAS = RegisterRiver(
    "Dravyavati River", frozenset({JAIPUR}), "RIVER_ALIASES:dravyavati", ("Amanisha Nallah", "Amanishah Nala")
)


def _row(row_id: int, name: str, districts: list[int], **named: Any) -> dict[str, Any]:
    return {"id": row_id, "name": name, "kind": "river", "districts": districts, **named, "lines": "AAAA"}


def _tile(*rows: dict[str, Any]) -> dict[str, Any]:
    return {
        "schemaVersion": 1,
        "tile": "e074n26",
        "bounds": [74, 26, 76, 28],
        "rivers": list(rows),
        "dams": [],
    }


def test_an_alias_answers_to_every_name_it_records_where_one_of_them_agrees() -> None:
    register = register_of([ALIAS])
    agreed = register.agreeing("Amanisha River", [JAIPUR])
    assert agreed == [ALIAS]
    assert accepted_names("Amanisha River", agreed) == [
        "Amanisha",
        "Amanisha Nallah",
        "Amanisha River",
        "Amanishah",
        "Amanishah Nala",
        "Dravyavati",
        "Dravyavati River",
    ]
    assert register.agreeing("Amanisha River", [KACHCHH]) == []
    assert register.agreeing("Amani Shah", [JAIPUR]) == []


def test_reading_the_register_again_names_a_row_and_keeps_its_lines_last() -> None:
    tiles = {"e074n26": _tile(_row(1, "Amanisha River", [JAIPUR]), _row(2, "Mashi", [JAIPUR]))}
    named, names = registered_waters(tiles, DATASET, register_of([ALIAS]))
    first, second = named["e074n26"]["rivers"]
    assert list(first) == ["id", "name", "kind", "districts", "also", "agrees", "lines"]
    assert first["agrees"] == [{"name": "Dravyavati River", "source": "RIVER_ALIASES:dravyavati"}]
    assert "Dravyavati" in first["also"] and "Amanisha River" not in first["also"]
    assert second == tiles["e074n26"]["rivers"][1]
    assert names["rivers"] == sorted({"Mashi", "Amanisha River", *first["also"]})
    assert names["datasets"] == [DATASET]


def test_a_name_the_register_no_longer_gives_is_taken_off_the_row() -> None:
    stale = _row(
        1, "Amanisha River", [JAIPUR], also=["Saraswati"], agrees=[{"name": "Saraswati", "source": "x"}]
    )
    named, names = registered_waters({"e074n26": _tile(stale)}, DATASET, register_of([]))
    assert named["e074n26"]["rivers"][0] == _row(1, "Amanisha River", [JAIPUR])
    assert names["rivers"] == ["Amanisha River"]


def test_the_files_are_rewritten_only_where_a_name_changed(tmp_path: Path) -> None:
    folder = tmp_path / WATERS_TILES
    folder.mkdir(parents=True)
    plain = _tile(_row(2, "Mashi", [JAIPUR]))
    (folder / "e074n26.json").write_text(
        layer_text(_tile(_row(1, "Amanisha River", [JAIPUR]))), encoding="utf-8"
    )
    (folder / "e076n26.json").write_text(layer_text({**plain, "tile": "e076n26"}), encoding="utf-8")
    (tmp_path / WATERS_NAMES).parent.mkdir(parents=True)
    (tmp_path / WATERS_NAMES).write_text(layer_text({"datasets": [DATASET]}), encoding="utf-8")
    assert reregister_files(tmp_path, register_of([ALIAS])) == ["e074n26"]
    renamed = json.loads((folder / "e074n26.json").read_text(encoding="utf-8"))
    assert "Dravyavati" in renamed["rivers"][0]["also"]
    assert "Dravyavati" in json.loads((tmp_path / WATERS_NAMES).read_text(encoding="utf-8"))["rivers"]
    assert reregister_files(tmp_path, register_of([ALIAS])) == []
