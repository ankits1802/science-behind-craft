from __future__ import annotations

import json
import shutil
from pathlib import Path

from app.curation.check_file import VERIFY_TOOL, verified_digest
from app.curation.checks import default_context
from app.curation.dossier import parse_dossier
from curation_support import FAILING, NOW, PASSING, recorded_reader

from curation.checking import check_run, stale_index_lines, write_index
from curation.verifying import failure_lines, verify_dossier, verify_file


def curation_dir(tmp_path: Path, fixture: Path = PASSING) -> Path:
    directory = tmp_path / "curation"
    directory.mkdir()
    shutil.copyfile(fixture, directory / "Kutch-Ajrakh.json")
    return directory


def rewrite_quote(path: Path, claim: int, quote: str) -> None:
    plain = json.loads(path.read_text(encoding="utf-8"))
    plain["claims"][claim]["quotes"][0]["quote"] = quote
    path.write_text(json.dumps(plain, indent=2) + "\n", encoding="utf-8", newline="\n")


def test_every_quote_of_the_passing_dossier_is_found_in_its_recorded_source() -> None:
    dossier = parse_dossier(PASSING.read_text(encoding="utf-8"))
    check = verify_dossier(dossier, recorded_reader(), now=lambda: NOW)
    assert [entry.result for entry in check.quotes] == ["PASS"] * 7
    assert check.tool == VERIFY_TOOL
    assert check.dossier_digest == verified_digest(dossier)
    assert [(source.source_id, source.route, source.read) for source in check.sources] == [
        ("S01", "LIVE", True),
        ("S02", "LIVE", True),
    ]
    assert failure_lines("Kutch-Ajrakh.json", check) == []


def test_a_quote_the_source_does_not_hold_fails() -> None:
    plain = json.loads(PASSING.read_text(encoding="utf-8"))
    plain["claims"][4]["quotes"][0]["quote"] = "Iron filings fermented with jaggery for about 12 days"
    dossier = parse_dossier(json.dumps(plain))
    check = verify_dossier(dossier, recorded_reader(), now=lambda: NOW)
    assert [entry.claim_id for entry in check.quotes if entry.result == "FAIL"] == ["C005"]
    assert failure_lines("Kutch-Ajrakh.json", check) == [
        "Kutch-Ajrakh.json: C005: quote not found in S01: 'Iron filings fermented with jaggery for about 12 days'"
    ]


def test_an_unreadable_source_fails_its_quotes_with_one_line() -> None:
    dossier = parse_dossier(PASSING.read_text(encoding="utf-8"))
    check = verify_dossier(dossier, recorded_reader(unread=frozenset({"S02"})), now=lambda: NOW)
    assert [entry.claim_id for entry in check.quotes if entry.result == "FAIL"] == ["C006", "C007"]
    assert failure_lines("K.json", check) == [
        "K.json: S02: could not be read: live page: HTTP 403; archive: the Wayback Machine has no snapshot"
    ]


def test_verify_then_check_passes_and_indexes_the_craft(tmp_path: Path) -> None:
    directory = curation_dir(tmp_path)
    lines, check = verify_file(directory / "Kutch-Ajrakh.json", recorded_reader())
    assert lines == []
    assert check is not None
    assert (directory / "Kutch-Ajrakh.check.json").is_file()
    outcome = check_run([], directory, default_context())
    assert outcome.lines == []
    entry = json.loads(outcome.index)["crafts"][0]
    assert (entry["craftSlug"], entry["check"]["status"], entry["check"]["problems"]) == (
        "Kutch-Ajrakh",
        "PASS",
        0,
    )


def test_editing_a_quote_after_verify_makes_the_check_file_stale(tmp_path: Path) -> None:
    directory = curation_dir(tmp_path)
    verify_file(directory / "Kutch-Ajrakh.json", recorded_reader())
    rewrite_quote(directory / "Kutch-Ajrakh.json", 0, "Ajrakh is printed on both sides of the cotton cloth")
    lines = check_run([], directory, default_context()).lines
    assert lines == [
        f"{directory / 'Kutch-Ajrakh.json'}: check file: the dossier's sources or quotes changed after it "
        "was verified; run verify again"
    ]


def test_a_dossier_without_its_check_file_fails(tmp_path: Path) -> None:
    directory = curation_dir(tmp_path)
    assert check_run([], directory, default_context()).lines == [
        f"{directory / 'Kutch-Ajrakh.json'}: check file: Kutch-Ajrakh.check.json is missing; run verify"
    ]


def test_the_failing_dossier_prints_one_line_per_problem(tmp_path: Path) -> None:
    directory = curation_dir(tmp_path, FAILING)
    lines = check_run([directory / "Kutch-Ajrakh.json"], directory, default_context()).lines
    assert len(lines) == 10
    assert lines[-1].endswith("check file: Kutch-Ajrakh.check.json is missing; run verify")


def test_stray_files_missing_targets_and_a_stale_index_are_reported(tmp_path: Path) -> None:
    directory = curation_dir(tmp_path)
    verify_file(directory / "Kutch-Ajrakh.json", recorded_reader())
    (directory / "notes.txt").write_text("draft\n", encoding="utf-8")
    (directory / "Bagru-Dabu.check.json").write_text("{}\n", encoding="utf-8")
    label = str(directory)
    assert check_run([], directory, default_context()).lines == [
        f"{label}: Bagru-Dabu.check.json: is a check file without its dossier",
        f"{label}: notes.txt: is not a dossier, a check file or the index",
    ]
    missing = directory / "Bagru-Dabu.json"
    assert check_run([missing], directory, default_context()).lines == [f"{missing}: file: does not exist"]
    outcome = check_run([], directory, default_context())
    assert stale_index_lines(directory, outcome.index) == [
        f"{directory / 'index.json'}: index: is not current; run python tools/curation/check.py and keep the file "
        "it writes"
    ]
    write_index(directory, outcome.index)
    assert stale_index_lines(directory, outcome.index) == []
