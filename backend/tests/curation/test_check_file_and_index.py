from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.curation.check_file import check_file_problems, check_file_text
from app.curation.dossier import dossier_schema_text
from app.curation.files import DossierResult
from app.curation.index import corroborated, curation_index, index_text
from app.curation.problems import Problem
from app.data.district_register import load_district_register, parse_district_register

from .builders import CHECKED_AT, changed_dossier, check_for, passing_dossier

REPO = Path(__file__).resolve().parents[3]
SCHEMA_FILE = REPO / "shared" / "curation.dossier.schema.json"


def messages(problems: list[Any]) -> list[tuple[str, str]]:
    return [(problem.where, problem.message) for problem in problems]


def test_a_fresh_check_file_passes() -> None:
    dossier = passing_dossier()
    assert check_file_problems(dossier, check_for(dossier)) == []


def test_a_missing_check_file_is_reported() -> None:
    assert messages(check_file_problems(passing_dossier(), None)) == [
        ("check file", "Kutch-Ajrakh.check.json is missing; run verify")
    ]


def test_a_check_file_goes_stale_when_a_quote_or_source_changes() -> None:
    check = check_for(passing_dossier())

    def requote(plain: dict[str, Any]) -> None:
        plain["claims"][0]["quotes"][0]["quote"] = "printed on both sides of the cotton cloth"

    def move(plain: dict[str, Any]) -> None:
        plain["sources"][0]["url"] = "https://example.org/test/block-printing-moved"

    stale = ("check file", "the dossier's sources or quotes changed after it was verified; run verify again")
    assert messages(check_file_problems(changed_dossier(requote), check)) == [stale]
    assert messages(check_file_problems(changed_dossier(move), check)) == [stale]


def test_prose_edits_keep_the_check_file_fresh() -> None:
    check = check_for(passing_dossier())

    def reword(plain: dict[str, Any]) -> None:
        plain["overview"]["keyFacts"][0]["label"] = "Main centre"

    assert check_file_problems(changed_dossier(reword), check) == []


def test_a_check_file_older_than_the_dossier_is_stale() -> None:
    check = check_for(passing_dossier())
    later = changed_dossier(lambda plain: plain.update(curatedAt="2026-11-17T13:00:00+05:30"))
    assert messages(check_file_problems(later, check)) == [
        ("check file", "the check file is older than the dossier's curatedAt; run verify again")
    ]


def test_a_check_file_from_another_verifier_is_stale() -> None:
    dossier = passing_dossier()
    check = check_for(dossier).model_copy(update={"tool": "kalavigyan-curation-verify/0"})
    assert messages(check_file_problems(dossier, check))[0][1].startswith(
        "the check file was made by kalavigyan-curation-verify/0"
    )


def test_every_kept_quote_must_have_passed() -> None:
    dossier = passing_dossier()
    check = check_for(dossier, failing=frozenset({"C004"}), unread=frozenset({"S02"}))
    assert messages(check_file_problems(dossier, check)) == [
        ("S02", "could not be read when verified (HTTP 403); drop it with its claims"),
        ("C004.quotes.0", "did not pass verify against S01; drop the quote"),
        ("C006.quotes.0", "did not pass verify against S02; drop the quote"),
        ("C007.quotes.0", "did not pass verify against S02; drop the quote"),
    ]


def test_check_file_text_round_trips() -> None:
    check = check_for(passing_dossier())
    plain = json.loads(check_file_text(check))
    assert plain["schemaVersion"] == 1
    assert plain["checkedAt"] == "2026-11-17T12:00:00+05:30"
    assert plain["quotes"][0] == {
        "claimId": "C001",
        "sourceId": "S01",
        "quote": "Ajrakh is printed on both sides of the cotton cloth with carved wooden blocks",
        "result": "PASS",
    }


def test_corroboration_needs_two_publishers() -> None:
    def second_quote(plain: dict[str, Any]) -> None:
        plain["claims"][0]["quotes"].append(
            {
                "sourceId": "S02",
                "locator": "para 1",
                "quote": "families of Khatri printers now work on ajrakh cloth",
            }
        )

    dossier = changed_dossier(second_quote)
    assert corroborated(dossier, dossier.claims[0]) is True
    assert corroborated(dossier, dossier.claims[1]) is False


PASSING_COUNTS = {
    "sources": 2,
    "claims": 7,
    "hypotheses": 0,
    "corroborated": 0,
    "places": 1,
    "communities": 1,
    "stages": 2,
    "orderedStages": 0,
    "materials": 2,
    "tools": 0,
    "reactions": 0,
    "environment": 1,
    "terms": 0,
    "conflicts": 0,
    "openQuestions": 0,
    "pictures": 0,
    "overviewSections": 0,
}
PASSING_DISCIPLINES = {
    "OVERVIEW": 1,
    "PROCESS": 1,
    "CHEMISTRY": 1,
    "MATERIALS": 1,
    "CLIMATE": 1,
    "HISTORY": 1,
    "ECONOMICS": 1,
}


def test_the_index_counts_each_part_of_a_dossier() -> None:
    dossier = passing_dossier()
    result = DossierResult(Path("Kutch-Ajrakh.json"), dossier, check_for(dossier), ())
    entry = json.loads(index_text(curation_index([result])))["crafts"][0]
    assert entry == {
        "craftSlug": "Kutch-Ajrakh",
        "file": "Kutch-Ajrakh.json",
        "version": 1,
        "coverage": "THIN",
        "curatedAt": "2026-11-17T10:00:00+05:30",
        "counts": PASSING_COUNTS,
        "claimsByDiscipline": PASSING_DISCIPLINES,
        "sourcesByReliability": {"A": 1, "B": 0, "C": 1, "D": 0},
        "check": {"status": "PASS", "problems": 0, "verifiedAt": CHECKED_AT.isoformat()},
    }


def test_an_unreadable_dossier_is_indexed_as_failing() -> None:
    result = DossierResult(Path("Broken-Craft.json"), None, None, ())
    failing = DossierResult(Path("Kutch-Ajrakh.json"), None, None, (Problem("file", "is not UTF-8 text"),))
    crafts = json.loads(index_text(curation_index([failing, result])))["crafts"]
    assert [(entry["craftSlug"], entry["check"]["status"]) for entry in crafts] == [
        ("Broken-Craft", "PASS"),
        ("Kutch-Ajrakh", "FAIL"),
    ]


def test_the_shared_schema_is_generated_from_the_model() -> None:
    assert SCHEMA_FILE.read_text(encoding="utf-8") == dossier_schema_text()


def test_the_district_register_names_states_districts_and_pending_districts() -> None:
    raw = {
        "states": [{"lgd": 24, "name": "Gujarat"}, {"lgd": 37, "name": "Ladakh"}],
        "districts": [{"lgd": 449, "stateLgd": 24, "name": "Kachchh"}],
        "pending": [{"state": "Ladakh", "district": "Nubra", "reason": "not listed yet"}],
    }
    register = parse_district_register(raw)
    assert register.states == frozenset({"Gujarat", "Ladakh"})
    assert register.has_district("Gujarat", "Kachchh")
    assert not register.has_district("Gujarat", "Kutch")
    assert register.has_district("Ladakh", "Nubra")
    real = load_district_register()
    assert real.has_district("Gujarat", "Kachchh")
    assert len(real.states) == 36
