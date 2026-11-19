from __future__ import annotations

import json
from collections import Counter
from dataclasses import replace
from typing import Any

import pytest

from app.core.errors import InvalidInput
from app.curation.dossier import Dossier
from app.services.dossier_diff import NOT_IN_GIT
from app.services.dossier_export import CHANGED, CURRENT, LAYOUT, MISSING, NEW, SAME, stored_export
from app.services.dossier_export_records import GitDossier, StoredCuration

from .export_support import git_of, stored_category_of, stored_craft_of
from .import_support import AJRAKH, raw

AJRAKH_CLAIMS = 143
AJRAKH_QUOTES = 284
LEATHER = "Leather-Craft-Category"
LAYOUT_ONLY = "Agra-Marble-Inlay"
DROPPING = "Stone-Others"
CATEGORY_KEPT = (
    "places",
    "communities",
    "stages",
    "materials",
    "tools",
    "environment",
    "nativeNames",
    "market",
)


def _quotes(plain: dict[str, Any]) -> Counter[tuple[str, str, str, str]]:
    return Counter(
        (claim["id"], quote["sourceId"], quote["locator"], quote["quote"])
        for claim in plain["claims"]
        for quote in claim["quotes"]
    )


def _with_git(git: GitDossier, plain: dict[str, Any]) -> GitDossier:
    return replace(git, text=json.dumps(plain), dossier=Dossier.model_validate(plain))


def _claim_id(stored: StoredCuration, key: str) -> Any:
    return next(claim_id for claim_id, row in stored.markers.items() if row["key"] == key)


def test_the_kutch_ajrakh_dossier_comes_back_as_the_file_in_git() -> None:
    found = stored_export(stored_craft_of(AJRAKH), git_of(AJRAKH))
    plain = raw(AJRAKH)
    assert (len(plain["claims"]), sum(_quotes(plain).values())) == (AJRAKH_CLAIMS, AJRAKH_QUOTES)
    assert found.text == git_of(AJRAKH).text
    assert (found.file, found.version, found.status, found.check) == (f"{AJRAKH}.json", 3, SAME, CURRENT)
    assert found.changes == () and found.reviewed == ()
    assert found.exported.carried == () and found.exported.failed_quotes == 0


def test_without_its_git_file_the_export_still_holds_every_record_the_import_stored() -> None:
    found = stored_export(stored_craft_of(AJRAKH), None)
    plain = raw(AJRAKH)
    exported = json.loads(found.text)
    assert (found.status, found.check, found.changes) == (NEW, MISSING, (NOT_IN_GIT,))
    assert {c["id"]: c["text"] for c in exported["claims"]} == {c["id"]: c["text"] for c in plain["claims"]}
    assert _quotes(exported) == _quotes(plain)
    assert exported["sources"] == plain["sources"]
    assert exported["market"]["gi"] == plain["market"]["gi"]
    assert exported["pictures"] == plain["pictures"]
    assert exported["reactions"] == plain["reactions"]
    assert [stage["id"] for stage in exported["stages"]] == [stage["id"] for stage in plain["stages"]]
    for ours, theirs in zip(exported["stages"], plain["stages"], strict=True):
        assert {k: v for k, v in ours.items() if k not in ("materials", "tools")} == {
            k: v for k, v in theirs.items() if k not in ("materials", "tools")
        }
        assert sorted(map(json.dumps, ours.get("materials", []))) == sorted(
            map(json.dumps, theirs.get("materials", []))
        )


def test_the_diff_names_each_change_against_the_dossier_in_git() -> None:
    plain = raw(AJRAKH)
    first, last = plain["claims"][0], plain["claims"][-1]
    plain["version"] = 4
    plain["claims"] = [
        {**first, "text": "An earlier wording of the first claim, kept only in git."},
        *plain["claims"][1:-1],
        {**last, "id": "C999"},
    ]
    found = stored_export(stored_craft_of(AJRAKH), _with_git(git_of(AJRAKH), plain))
    assert found.status == CHANGED
    assert found.changes == (
        "version: 4 in git, 3 stored",
        f"claims: added {last['id']}; removed C999; changed {first['id']} (text)",
    )
    assert found.check == CURRENT


def test_a_claim_a_review_withdrew_is_reported() -> None:
    stored = stored_craft_of(AJRAKH)
    claim_id = _claim_id(stored, "C001")
    claims = {**stored.claims, claim_id: {**stored.claims[claim_id], "status": "RETRACTED"}}
    found = stored_export(replace(stored, claims=claims), git_of(AJRAKH))
    assert found.reviewed == ("C001: RETRACTED",)
    assert found.status == SAME


def test_a_source_the_dossier_does_not_own_is_refused_without_git() -> None:
    stored = stored_craft_of(AJRAKH)
    source_id, row = next(iter(stored.sources.items()))
    sources = {**stored.sources, source_id: {**row, "externalIds": {}, "doi": None}}
    with pytest.raises(InvalidInput, match="neither the dossier's own"):
        stored_export(replace(stored, sources=sources), None)


def test_a_file_laid_out_by_hand_differs_only_in_layout() -> None:
    found = stored_export(stored_craft_of(LAYOUT_ONLY), git_of(LAYOUT_ONLY))
    assert (found.status, found.changes) == (LAYOUT, ())
    assert found.exported.dossier == git_of(LAYOUT_ONLY).dossier


def test_a_sentence_the_import_dropped_is_kept_from_git() -> None:
    stored = stored_craft_of(DROPPING)
    shown = {sentence.text for sentences in stored.sentences.values() for sentence in sentences}
    overview = raw(DROPPING)["overview"]
    parts = [("lede", overview.get("lede", []))]
    parts += [(section["discipline"], section["sentences"]) for section in overview.get("sections", [])]
    dropped = [
        f"overview.{part}.{index}"
        for part, sentences in parts
        for index, sentence in enumerate(sentences)
        if sentence["text"] not in shown
    ]
    found = stored_export(stored, git_of(DROPPING))
    assert dropped
    assert [line.split(":")[0] for line in found.exported.carried] == dropped
    assert found.status == SAME


def test_a_category_comes_back_with_the_parts_git_keeps() -> None:
    git = git_of(LEATHER, category=True)
    found = stored_export(stored_category_of(LEATHER), git)
    plain = raw(f"categories/{LEATHER}")
    kept = [part for part in CATEGORY_KEPT if plain.get(part) not in (None, [], {})]
    assert found.text == git.text
    assert (found.file, found.status, found.check) == (f"categories/{LEATHER}.json", SAME, CURRENT)
    note = found.exported.carried[0]
    named = note.split(":")[0].split(", ")
    assert [name for name in named if name != "the stages of reactions"] == [
        "native_names" if part == "nativeNames" else part for part in kept
    ]


def test_a_category_needs_its_dossier_in_git() -> None:
    with pytest.raises(InvalidInput, match="cannot be exported without its dossier in git"):
        stored_export(stored_category_of(LEATHER), None)


def test_a_category_whose_git_version_differs_is_refused() -> None:
    plain = raw(f"categories/{LEATHER}")
    plain["version"] += 1
    git = _with_git(git_of(LEATHER, category=True), plain)
    with pytest.raises(InvalidInput, match="import or restore the version the database holds first"):
        stored_export(stored_category_of(LEATHER), git)
