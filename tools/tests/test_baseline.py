from __future__ import annotations

import json
from pathlib import Path

import pytest

from hygiene.baseline import BaselineError, compare, read_baseline, write_baseline

COUNTS = {"oversizedFiles": 3, "longFunctions": 10, "wideFunctions": 0}


def test_written_baseline_reads_back(tmp_path: Path) -> None:
    path = tmp_path / "baseline.json"
    write_baseline(path, COUNTS)
    assert read_baseline(path) == COUNTS


def test_written_file_is_lf_utf8_json(tmp_path: Path) -> None:
    path = tmp_path / "baseline.json"
    write_baseline(path, COUNTS)
    raw = path.read_bytes()
    assert b"\r" not in raw and raw.endswith(b"}\n")
    assert json.loads(raw) == {"schemaVersion": 1, "counts": COUNTS}


def test_missing_baseline_fails_loudly(tmp_path: Path) -> None:
    with pytest.raises(BaselineError, match="--update-baseline"):
        read_baseline(tmp_path / "absent.json")


@pytest.mark.parametrize(
    "payload",
    [
        {"schemaVersion": 2, "counts": COUNTS},
        {"counts": COUNTS},
        {"schemaVersion": 1, "counts": {"oversizedFiles": 1}},
        {"schemaVersion": 1, "counts": {**COUNTS, "extra": 1}},
        {"schemaVersion": 1, "counts": {**COUNTS, "wideFunctions": -1}},
        {"schemaVersion": 1, "counts": {**COUNTS, "wideFunctions": True}},
        {"schemaVersion": 1, "counts": {**COUNTS, "wideFunctions": "2"}},
        [],
    ],
)
def test_malformed_baseline_is_refused(tmp_path: Path, payload: object) -> None:
    path = tmp_path / "baseline.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(BaselineError):
        read_baseline(path)


def test_compare_marks_rises_and_falls() -> None:
    steps = compare(COUNTS, {"oversizedFiles": 4, "longFunctions": 9, "wideFunctions": 0})
    assert [(step.name, step.rose, step.fell) for step in steps] == [
        ("oversizedFiles", True, False),
        ("longFunctions", False, True),
        ("wideFunctions", False, False),
    ]
