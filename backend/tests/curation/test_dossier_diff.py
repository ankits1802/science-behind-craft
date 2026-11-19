from __future__ import annotations

import json
from pathlib import Path

from app.curation.dossier import Dossier
from app.curation.dossier_text import dossier_text
from app.scripts.export_dossiers import write_exports
from app.services.dossier_diff import dossier_changes
from app.services.dossier_export import ExportRun, stored_export

from .export_support import git_of, stored_category_of, stored_craft_of
from .import_support import AJRAKH, raw

LEATHER = "Leather-Craft-Category"
ONE_SPACE = "Bidriware"


def _dossier(plain: dict) -> Dossier:
    return Dossier.model_validate(plain)


def test_only_a_new_order_is_reported_as_reordered() -> None:
    plain = raw(AJRAKH)
    moved = {**plain, "claims": [*plain["claims"][1:], plain["claims"][0]]}
    assert dossier_changes(_dossier(plain), _dossier(moved)) == ("claims: reordered",)


def test_a_long_list_of_names_is_cut_after_twelve() -> None:
    plain = raw(AJRAKH)
    fewer = {**plain, "claims": plain["claims"][:-14]}
    added = ", ".join(claim["id"] for claim in plain["claims"][-14:-2])
    assert dossier_changes(_dossier(plain), _dossier(fewer)) == (f"claims: added {added} and 2 more",)


def test_a_part_without_ids_is_reported_whole() -> None:
    plain = raw(AJRAKH)
    priced = {**plain, "market": {**plain["market"], "prices": []}}
    assert dossier_changes(_dossier(plain), _dossier(priced)) == ("market: changed",)


def test_the_text_keeps_the_key_order_and_empty_parts_of_the_file_in_git() -> None:
    git = git_of(LEATHER, category=True)
    plain = json.loads(git.text)
    assert list(plain)[1:3] == ["scope", "categorySlug"] and plain["tools"] == []
    assert dossier_text(git.dossier, like=git.text) == git.text
    bare = json.loads(dossier_text(git.dossier))
    assert list(bare)[1:3] == ["categorySlug", "scope"] and "tools" not in bare


def test_the_text_keeps_the_indent_of_the_file_in_git() -> None:
    git = git_of(ONE_SPACE)
    assert git.text.splitlines()[1].startswith(' "')
    assert dossier_text(git.dossier, like=git.text) == git.text
    assert dossier_text(git.dossier).splitlines()[1].startswith('  "')


def test_an_export_writes_only_the_files_that_differ(tmp_path: Path) -> None:
    same = stored_export(stored_craft_of(AJRAKH), git_of(AJRAKH))
    category = stored_export(stored_category_of(LEATHER), git_of(LEATHER, category=True))
    (tmp_path / same.file).write_text(same.text, encoding="utf-8", newline="\n")
    written = write_exports(ExportRun(exports=(same, category), refused=()), tmp_path)
    assert written == [f"categories/{LEATHER}.json"]
    assert (tmp_path / "categories" / f"{LEATHER}.json").read_text(encoding="utf-8") == category.text
