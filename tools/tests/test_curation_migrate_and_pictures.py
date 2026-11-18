from __future__ import annotations

import json
from pathlib import Path

import pytest
from curation_support import PASSING, FakeHttp, fetched

from curation.commons import PictureFailed, commons_picture, imageinfo_url, picture_lines
from curation.migrating import MigrationFailed, main as migrate_main, migrate_files, migrated_text
from curation.polite import FetchFailed

FILE_PAGE = "https://commons.wikimedia.org/wiki/File:KING_PRIEST.jpg"
SCHEMA_1 = '{\n  "schemaVersion": 1,\n  "craftSlug": "Kutch-Ajrakh",\n  "nested": {"schemaVersion": 1}\n}\n'


def imageinfo(**info: object) -> bytes:
    page = {"ns": 6, "title": "File:KING PRIEST.jpg", "imageinfo": [info]}
    return json.dumps({"batchcomplete": True, "query": {"pages": [page]}}).encode()


def king_priest() -> bytes:
    return imageinfo(
        width=1424,
        height=2000,
        url="https://upload.wikimedia.org/wikipedia/commons/b/bd/KING_PRIEST.jpg?utm_source=commons.wikimedia.org",
        extmetadata={
            "Artist": {"value": '<a href="//commons.wikimedia.org/wiki/User:Irfanmurtaza">Irfanmurtaza</a>'},
            "LicenseShortName": {"value": "CC BY-SA 4.0"},
            "LicenseUrl": {"value": "https://creativecommons.org/licenses/by-sa/4.0"},
        },
    )


def test_migration_changes_the_schema_version_alone() -> None:
    assert migrated_text(SCHEMA_1) == (
        '{\n  "schemaVersion": 2,\n  "craftSlug": "Kutch-Ajrakh",\n  "nested": {"schemaVersion": 1}\n}\n'
    )
    assert migrated_text(SCHEMA_1.replace('"schemaVersion": 1,', '"schemaVersion": 2,', 1)) is None


@pytest.mark.parametrize(
    ("text", "reason"),
    [
        ('{"craftSlug": "Kutch-Ajrakh"}', "is not a dossier: it has no schemaVersion"),
        ('{"schemaVersion": 7}', "has schemaVersion 7; only 1 migrates"),
        ('{"schemaVersion": 1.0}', "its schemaVersion could not be rewritten alone"),
    ],
)
def test_migration_refuses_what_is_not_a_schema_1_dossier(text: str, reason: str) -> None:
    with pytest.raises(MigrationFailed, match=reason):
        migrated_text(text)


def test_migrating_files_writes_only_what_changes_and_a_failure_writes_nothing(tmp_path: Path) -> None:
    old = tmp_path / "Kutch-Ajrakh.json"
    current = tmp_path / "Bagru-Hand-Block-Print.json"
    broken = tmp_path / "Broken.json"
    old.write_text(SCHEMA_1, encoding="utf-8", newline="\n")
    current.write_text('{\n  "schemaVersion": 2\n}\n', encoding="utf-8", newline="\n")
    outcome = migrate_files([old, current])
    assert (outcome.rewritten, outcome.current) == ((old,), (current,))
    assert json.loads(old.read_text(encoding="utf-8"))["schemaVersion"] == 2
    old.write_text(SCHEMA_1, encoding="utf-8", newline="\n")
    broken.write_text("{not json", encoding="utf-8")
    with pytest.raises(MigrationFailed, match=r"Broken.json"):
        migrate_files([old, broken])
    assert old.read_text(encoding="utf-8") == SCHEMA_1


def test_the_migrate_command_rewrites_the_folder_and_its_categories(tmp_path: Path, capsys) -> None:
    (tmp_path / "categories").mkdir()
    (tmp_path / "Kutch-Ajrakh.json").write_text(SCHEMA_1, encoding="utf-8", newline="\n")
    (tmp_path / "Kutch-Ajrakh.check.json").write_text('{"schemaVersion": 1}\n', encoding="utf-8")
    (tmp_path / "categories" / "Stone-Craft-Category.json").write_text(
        SCHEMA_1, encoding="utf-8", newline="\n"
    )
    assert migrate_main(["--dir", str(tmp_path)]) == 0
    assert capsys.readouterr().out.splitlines()[-1] == "migrated 2, already current 0"
    assert json.loads((tmp_path / "Kutch-Ajrakh.check.json").read_text(encoding="utf-8")) == {
        "schemaVersion": 1
    }


def test_the_passing_fixture_is_already_current() -> None:
    assert migrated_text(PASSING.read_text(encoding="utf-8")) is None


def test_the_picture_reader_asks_commons_for_size_and_credit() -> None:
    url = imageinfo_url(FILE_PAGE)
    assert url.startswith("https://commons.wikimedia.org/w/api.php?action=query&format=json&formatversion=2")
    assert "iiprop=url%7Csize%7Cextmetadata" in url and "titles=File%3AKING+PRIEST.jpg" in url
    http = FakeHttp({url: fetched(url, king_priest(), "application/json")})
    picture = commons_picture(http, FILE_PAGE)
    assert http.asked == [url]
    assert picture_lines(picture) == [
        "pageUrl: https://commons.wikimedia.org/wiki/File:KING_PRIEST.jpg",
        "url: https://upload.wikimedia.org/wikipedia/commons/b/bd/KING_PRIEST.jpg",
        "width: 1424",
        "height: 2000",
        "author: Irfanmurtaza",
        "licence: CC BY-SA 4.0",
        "licenceUrl: https://creativecommons.org/licenses/by-sa/4.0",
    ]


def test_a_file_page_name_is_read_with_spaces_and_escapes_decoded() -> None:
    url = imageinfo_url(
        "https://commons.wikimedia.org/wiki/File:08-Indigo-factory-%28beating-the-Vats%29-bw.jpg"
    )
    assert "titles=File%3A08-Indigo-factory-%28beating-the-Vats%29-bw.jpg" in url


@pytest.mark.parametrize(
    ("answer", "reason"),
    [
        (imageinfo(url="https://upload.wikimedia.org/x.jpg"), "gives no width and height"),
        (imageinfo(width=10, height=20), "gives no https address"),
        (
            json.dumps({"query": {"pages": [{"title": "File:X.jpg", "missing": True}]}}).encode(),
            "has no file",
        ),
        (b"<html>", "something other than JSON"),
    ],
)
def test_the_picture_reader_refuses_an_answer_without_a_sized_file(answer: bytes, reason: str) -> None:
    url = imageinfo_url(FILE_PAGE)
    with pytest.raises(PictureFailed, match=reason):
        commons_picture(FakeHttp({url: fetched(url, answer, "application/json")}), FILE_PAGE)


def test_the_picture_reader_refuses_other_pages_and_reports_a_failed_request() -> None:
    with pytest.raises(PictureFailed, match="is not a Wikimedia Commons file page"):
        imageinfo_url("https://en.wikipedia.org/wiki/Ajrak")
    url = imageinfo_url(FILE_PAGE)
    with pytest.raises(PictureFailed, match=r"could not read .*: HTTP 429"):
        commons_picture(FakeHttp({url: FetchFailed(url, "HTTP 429")}), FILE_PAGE)
