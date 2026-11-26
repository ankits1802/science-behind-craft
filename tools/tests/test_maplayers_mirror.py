from __future__ import annotations

import json
from pathlib import Path

from basemap.polyline import decode_records
from maplayers.mirror import (
    BASE_FILES,
    INDIA_SOURCE,
    MEASURED_FILES,
    MEASURED_OUTPUT,
    OUTLINE_FILE,
    mirror_base,
    mirror_measured,
    mirror_waters,
    unmirrored,
    unmirrored_base,
    unmirrored_waters,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
DRAWN = REPO_ROOT / "frontend" / "public" / "layers"


def test_the_api_measures_from_the_same_layer_files_the_map_draws() -> None:
    assert MEASURED_FILES == ("relief.json", "rivers.json", "minerals.json")
    assert unmirrored(DRAWN, REPO_ROOT / MEASURED_OUTPUT) == []


def test_the_api_draws_paper_maps_on_the_outline_and_state_lines_the_web_map_draws() -> None:
    assert BASE_FILES == ("state-borders.json",)
    assert unmirrored_base(REPO_ROOT) == [], "run tools/maplayers_mirror.py"
    outline = json.loads((REPO_ROOT / MEASURED_OUTPUT / OUTLINE_FILE).read_text(encoding="utf-8"))
    rings = decode_records(outline["payload"], True)
    assert rings and all(len(points) >= 3 for _, points in rings)
    assert not rings[0][0]


def test_a_base_mirror_follows_its_sources(tmp_path: Path) -> None:
    (tmp_path / INDIA_SOURCE).parent.mkdir(parents=True)
    (tmp_path / INDIA_SOURCE).write_text('const PAYLOAD =\n  "abc" +\n  "def";\n', encoding="utf-8")
    boundaries = tmp_path / "frontend" / "public" / "boundaries"
    boundaries.mkdir(parents=True)
    (boundaries / "state-borders.json").write_text('{"schemaVersion":1,"lines":"Ew"}\n', encoding="utf-8")
    assert unmirrored_base(tmp_path) == ["state-borders.json", OUTLINE_FILE]
    mirror_base(tmp_path)
    assert unmirrored_base(tmp_path) == []
    held = json.loads((tmp_path / MEASURED_OUTPUT / OUTLINE_FILE).read_text(encoding="utf-8"))
    assert held == {"schemaVersion": 1, "payload": "abcdef"}
    (boundaries / "state-borders.json").write_text('{"schemaVersion":1,"lines":"Fw"}\n', encoding="utf-8")
    assert unmirrored_base(tmp_path) == ["state-borders.json"]


def test_a_build_mirrors_each_measured_layer_byte_for_byte(tmp_path: Path) -> None:
    drawn, measured = tmp_path / "drawn", tmp_path / "measured"
    drawn.mkdir()
    for at, name in enumerate(MEASURED_FILES):
        (drawn / name).write_bytes(f'{{"layer":{at}}}\n'.encode())
    assert unmirrored(drawn, measured) == list(MEASURED_FILES)
    written = mirror_measured(drawn, measured)
    assert [path.name for path in written] == list(MEASURED_FILES)
    assert (measured / "rivers.json").read_text(encoding="utf-8") == '{"layer":1}\n'
    assert unmirrored(drawn, measured) == []
    (measured / "minerals.json").write_text("{}\n", encoding="utf-8")
    assert unmirrored(drawn, measured) == ["minerals.json"]


def test_the_api_prints_the_small_waters_the_web_map_draws() -> None:
    assert unmirrored_waters(REPO_ROOT) == [], "run tools/maplayers_mirror.py"


def test_a_waters_mirror_follows_its_tiles_and_drops_a_tile_the_web_no_longer_draws(tmp_path: Path) -> None:
    drawn = tmp_path / "frontend" / "public" / "layers"
    (drawn / "waters").mkdir(parents=True)
    (drawn / "waters.json").write_text('{"schemaVersion":1,"tiles":[]}\n', encoding="utf-8")
    for tile in ("e070n22", "e074n26"):
        (drawn / "waters" / f"{tile}.json").write_text(f'{{"tile":"{tile}"}}\n', encoding="utf-8")
    assert unmirrored_waters(tmp_path) == ["waters.json", "waters/e070n22.json", "waters/e074n26.json"]
    mirror_waters(tmp_path)
    assert unmirrored_waters(tmp_path) == []
    measured = tmp_path / MEASURED_OUTPUT / "waters"
    (drawn / "waters" / "e074n26.json").unlink()
    (drawn / "waters" / "e070n22.json").write_text('{"tile":"e070n22","renamed":true}\n', encoding="utf-8")
    assert unmirrored_waters(tmp_path) == ["waters/e070n22.json", "waters/e074n26.json"]
    mirror_waters(tmp_path)
    assert sorted(path.name for path in measured.glob("*.json")) == ["e070n22.json"]
    assert unmirrored_waters(tmp_path) == []
