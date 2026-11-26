from __future__ import annotations

import io
import json
import zipfile
from collections.abc import Callable
from pathlib import Path

import pytest

from maplayers.fetch import (
    ATTEMPTS,
    LONGEST_WAIT,
    FetchFailed,
    Refused,
    Wanted,
    fetch_all,
    fetch_one,
    map_downloads,
    waits,
)
from maplayers.sources import ETOPO, MRDS, OSM_WATERS, Downloads

GRID = b"ncols 1993\nnrows 1921\nxllcorner 65\nyllcorner 5.6\ncellsize 0.0166667\n1 2 3\n"
HTML = b"<!doctype html><title>Forbidden</title>"
PBF = b"\x00\x00\x00\x0d\n\tOSMHeader\x18\x9a\x01"
PRIMARY, MIRROR = ETOPO.url, ETOPO.mirrors[0]


def answers(script: dict[str, list[bytes | Refused]]) -> tuple[Callable[[str, Path], None], list[str]]:
    asked: list[str] = []

    def opener(address: str, part: Path) -> None:
        asked.append(address)
        answer = script[address].pop(0)
        if isinstance(answer, Refused):
            part.write_bytes(b"partial")
            raise answer
        part.write_bytes(answer)

    return opener, asked


def shapefile_zip(name: str, *, holds_shp: bool = True) -> bytes:
    body = io.BytesIO()
    with zipfile.ZipFile(body, "w") as archive:
        archive.writestr(f"{name}.dbf", b"dbf")
        if holds_shp:
            archive.writestr(f"{name}.shp", b"shp")
        archive.writestr(f"{name}.VERSION.txt", b"5.1.1\n")
    return body.getvalue()


def etopo() -> Wanted:
    return map_downloads(["etopo1"])[0]


def test_each_address_waits_longer_between_tries_and_never_past_the_cap() -> None:
    assert waits() == [10.0, 20.0, 40.0]
    assert len(waits()) == ATTEMPTS - 1
    assert waits(8)[-1] == LONGEST_WAIT


def test_a_refusal_is_tried_again_after_a_growing_wait_and_the_address_that_answered_is_noted(
    tmp_path: Path,
) -> None:
    opener, asked = answers({PRIMARY: [Refused("HTTP 403"), Refused("HTTP 403"), GRID]})
    slept: list[float] = []
    done = fetch_all([etopo()], tmp_path, opener=opener, sleep=slept.append)
    assert asked == [PRIMARY] * 3
    assert slept == [10.0, 20.0]
    assert [each.address for each in done] == [PRIMARY]
    assert (tmp_path / ETOPO.file).read_bytes() == GRID
    assert not list(tmp_path.glob("*.part"))
    assert json.loads((tmp_path / "fetched.json").read_text(encoding="utf-8")) == {ETOPO.file: PRIMARY}


def test_an_address_that_keeps_refusing_gives_way_to_the_mirror_whose_address_the_build_records(
    tmp_path: Path,
) -> None:
    opener, asked = answers({PRIMARY: [Refused("HTTP 403")] * ATTEMPTS, MIRROR: [GRID]})
    slept: list[float] = []
    fetch_all([etopo()], tmp_path, opener=opener, sleep=slept.append)
    assert asked == [PRIMARY] * ATTEMPTS + [MIRROR]
    assert slept == waits()
    assert Downloads(tmp_path).address(ETOPO.file, ETOPO.url) == MIRROR


def test_a_missing_file_is_not_asked_for_again_and_the_server_s_wait_is_kept_to_the_cap(
    tmp_path: Path,
) -> None:
    opener, asked = answers(
        {PRIMARY: [Refused("HTTP 404", again=False)], MIRROR: [Refused("HTTP 429", wait=600), GRID]}
    )
    slept: list[float] = []
    fetch_one(etopo(), tmp_path, opener=opener, sleep=slept.append)
    assert asked == [PRIMARY, MIRROR, MIRROR]
    assert slept == [LONGEST_WAIT]


def test_it_fails_only_when_every_address_fails_and_names_each_with_its_reason(tmp_path: Path) -> None:
    opener, asked = answers(
        {PRIMARY: [Refused("HTTP 403")] * ATTEMPTS, MIRROR: [Refused("HTTP 503")] * ATTEMPTS}
    )
    with pytest.raises(FetchFailed) as failed:
        fetch_all([etopo()], tmp_path, opener=opener, sleep=lambda _: None)
    assert len(asked) == 2 * ATTEMPTS
    assert failed.value.tried == ((PRIMARY, "HTTP 403"), (MIRROR, "HTTP 503"))
    assert str(failed.value).startswith(f"{ETOPO.file} could not be had from any of its 2 sources: ")
    assert PRIMARY in str(failed.value) and MIRROR in str(failed.value)
    assert not (tmp_path / ETOPO.file).exists() and not list(tmp_path.glob("*.part"))


def test_a_page_in_place_of_the_grid_is_refused_and_tried_again(tmp_path: Path) -> None:
    opener, asked = answers({PRIMARY: [HTML, GRID]})
    slept: list[float] = []
    fetch_one(etopo(), tmp_path, opener=opener, sleep=slept.append)
    assert asked == [PRIMARY, PRIMARY] and slept == [10.0]
    assert (tmp_path / ETOPO.file).read_bytes() == GRID


def test_a_grid_the_cache_kept_is_not_downloaded_and_a_broken_one_is(tmp_path: Path) -> None:
    (tmp_path / ETOPO.file).write_bytes(GRID)
    opener, asked = answers({})
    assert fetch_one(etopo(), tmp_path, opener=opener, sleep=lambda _: None).address is None
    assert asked == []
    assert Downloads(tmp_path).address(ETOPO.file, ETOPO.url) == ETOPO.url
    (tmp_path / ETOPO.file).write_bytes(HTML)
    opener, asked = answers({PRIMARY: [GRID]})
    assert fetch_one(etopo(), tmp_path, opener=opener, sleep=lambda _: None).address == PRIMARY


def test_a_natural_earth_zip_is_unpacked_only_when_it_holds_its_shapefile(tmp_path: Path) -> None:
    rivers = map_downloads(["rivers"])[0]
    name = rivers.unpack
    assert name is not None and rivers.addresses[0].startswith("https://naciscdn.org/")
    assert rivers.addresses[1] == f"https://naturalearth.s3.amazonaws.com/10m_physical/{name}.zip"
    bare, whole = shapefile_zip(name, holds_shp=False), shapefile_zip(name)
    opener, asked = answers({rivers.addresses[0]: [bare] * ATTEMPTS, rivers.addresses[1]: [whole]})
    fetch_one(rivers, tmp_path, opener=opener, sleep=lambda _: None)
    assert asked == [rivers.addresses[0]] * ATTEMPTS + [rivers.addresses[1]]
    assert (tmp_path / name / f"{name}.shp").read_bytes() == b"shp"


def test_the_extract_and_the_mineral_sites_are_checked_for_their_format(tmp_path: Path) -> None:
    osm, mrds = map_downloads(["osm", "mrds"])
    assert osm.addresses == (OSM_WATERS.url, *OSM_WATERS.mirrors) and mrds.addresses == (MRDS.url,)
    assert osm.check(_written(tmp_path / "a.pbf", PBF)) is None
    assert osm.check(_written(tmp_path / "b.pbf", HTML)) == "not an OpenStreetMap PBF file"
    assert mrds.check(_written(tmp_path / "c.zip", HTML)) == "not a zip archive"
    assert mrds.check(_written(tmp_path / "d.zip", shapefile_zip("mrds"))) is None


def test_every_download_is_named_and_an_unknown_name_is_refused() -> None:
    assert [each.file for each in map_downloads()][-3:] == [ETOPO.file, MRDS.file, OSM_WATERS.file]
    assert len(map_downloads()) == 7
    with pytest.raises(ValueError, match="no download is named hydrorivers"):
        map_downloads(["hydrorivers"])


def _written(path: Path, body: bytes) -> Path:
    path.write_bytes(body)
    return path
