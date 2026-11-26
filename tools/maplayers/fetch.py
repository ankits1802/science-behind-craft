from __future__ import annotations

import http.client
import json
import urllib.error
import urllib.request
import zipfile
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path

from .sources import (
    ETOPO,
    FETCHED_NOTE,
    MRDS,
    NATURAL_EARTH,
    OSM_WATERS,
    Source,
    natural_earth_addresses,
)

__all__ = [
    "AGENT",
    "ATTEMPTS",
    "FIRST_WAIT",
    "LONGEST_WAIT",
    "FetchFailed",
    "Fetched",
    "Opener",
    "Refused",
    "Wanted",
    "fetch_all",
    "fetch_one",
    "map_downloads",
    "url_opener",
    "waits",
]

AGENT = "KalaVigyan map layers build (GitHub Actions)"
ATTEMPTS = 4
FIRST_WAIT = 10.0
WAIT_FACTOR = 2.0
LONGEST_WAIT = 120.0
READ_SECONDS = 120
CHUNK = 1 << 20
HEAD_BYTES = 256
PART = ".part"
FINAL = frozenset({400, 401, 404, 405, 410, 414, 451})
PBF_HEADER = b"OSMHeader"


class Refused(Exception):
    def __init__(self, reason: str, *, again: bool = True, wait: float | None = None) -> None:
        super().__init__(reason)
        self.reason = reason
        self.again = again
        self.wait = wait


Opener = Callable[[str, Path], None]
Sleep = Callable[[float], None]
Check = Callable[[Path], str | None]


@dataclass(frozen=True)
class Wanted:
    file: str
    addresses: tuple[str, ...]
    check: Check
    unpack: str | None = None


@dataclass(frozen=True)
class Fetched:
    file: str
    address: str | None


class FetchFailed(Exception):
    def __init__(self, file: str, tried: Sequence[tuple[str, str]]) -> None:
        reasons = "; ".join(f"{address} ({reason})" for address, reason in tried)
        super().__init__(f"{file} could not be had from any of its {len(tried)} sources: {reasons}")
        self.file = file
        self.tried = tuple(tried)


def waits(attempts: int = ATTEMPTS) -> list[float]:
    return [min(FIRST_WAIT * WAIT_FACTOR**at, LONGEST_WAIT) for at in range(attempts - 1)]


def fetch_one(wanted: Wanted, folder: Path, *, opener: Opener, sleep: Sleep) -> Fetched:
    target = folder / wanted.file
    if target.is_file() and wanted.check(target) is None:
        _unpacked(wanted, target)
        return Fetched(wanted.file, None)
    tried = []
    for address in wanted.addresses:
        reason = _from(address, wanted, target, opener=opener, sleep=sleep)
        if reason is None:
            _unpacked(wanted, target)
            return Fetched(wanted.file, address)
        tried.append((address, reason))
    raise FetchFailed(wanted.file, tuple(tried))


def fetch_all(wanted: Iterable[Wanted], folder: Path, *, opener: Opener, sleep: Sleep) -> list[Fetched]:
    folder.mkdir(parents=True, exist_ok=True)
    done = [fetch_one(each, folder, opener=opener, sleep=sleep) for each in wanted]
    _note(folder, done)
    return done


def _from(address: str, wanted: Wanted, target: Path, *, opener: Opener, sleep: Sleep) -> str | None:
    part = target.with_name(target.name + PART)
    pauses = [*waits(), None]
    for pause in pauses:
        try:
            _kept(address, wanted, part, opener)
        except Refused as refused:
            part.unlink(missing_ok=True)
            if not refused.again or pause is None:
                return refused.reason
            sleep(min(refused.wait, LONGEST_WAIT) if refused.wait is not None else pause)
            continue
        part.replace(target)
        return None
    raise ValueError("a download is tried at least once")


def _kept(address: str, wanted: Wanted, part: Path, opener: Opener) -> None:
    opener(address, part)
    problem = wanted.check(part)
    if problem is not None:
        raise Refused(problem)


def _unpacked(wanted: Wanted, target: Path) -> None:
    if wanted.unpack is None:
        return
    with zipfile.ZipFile(target) as archive:
        archive.extractall(target.parent / wanted.unpack)


def _note(folder: Path, done: Sequence[Fetched]) -> None:
    path = folder / FETCHED_NOTE
    noted = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}
    noted.update({each.file: each.address for each in done if each.address is not None})
    path.write_text(json.dumps(noted, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")


def _head(path: Path) -> bytes:
    with path.open("rb") as handle:
        return handle.read(HEAD_BYTES)


def grid_check(path: Path) -> str | None:
    return None if b"ncols" in _head(path).lower() else "not an ESRI ASCII grid"


def pbf_check(path: Path) -> str | None:
    return None if PBF_HEADER in _head(path) else "not an OpenStreetMap PBF file"


def zip_check(member: str | None) -> Check:
    def check(path: Path) -> str | None:
        if not zipfile.is_zipfile(path):
            return "not a zip archive"
        if member is None:
            return None
        with zipfile.ZipFile(path) as archive:
            return None if member in archive.namelist() else f"a zip archive holding no {member}"

    return check


def map_downloads(keys: Sequence[str] | None = None) -> list[Wanted]:
    shapefiles = [
        Wanted(f"{name}.zip", natural_earth_addresses(key), zip_check(f"{name}.shp"), unpack=name)
        for key, (_, name) in NATURAL_EARTH.items()
    ]
    found = {
        **dict(zip(NATURAL_EARTH, shapefiles, strict=True)),
        "etopo1": _wanted(ETOPO, grid_check),
        "mrds": _wanted(MRDS, zip_check(None)),
        "osm": _wanted(OSM_WATERS, pbf_check),
    }
    unknown = sorted(set(keys or ()) - found.keys())
    if unknown:
        raise ValueError(f"no download is named {', '.join(unknown)}: choose from {', '.join(found)}")
    return [found[key] for key in keys] if keys else list(found.values())


def _wanted(source: Source, check: Check) -> Wanted:
    return Wanted(source.file, (source.url, *source.mirrors), check)


def url_opener(agent: str = AGENT, *, seconds: float = READ_SECONDS) -> Opener:
    def opened(address: str, part: Path) -> None:
        request = urllib.request.Request(address, headers={"User-Agent": agent})
        try:
            with urllib.request.urlopen(request, timeout=seconds) as answer, part.open("wb") as kept:
                for chunk in iter(lambda: answer.read(CHUNK), b""):
                    kept.write(chunk)
        except urllib.error.HTTPError as refused:
            raise Refused(
                f"HTTP {refused.code}", again=refused.code not in FINAL, wait=_retry_after(refused)
            ) from None
        except (urllib.error.URLError, http.client.HTTPException, OSError) as failed:
            raise Refused(type(failed).__name__) from None

    return opened


def _retry_after(refused: urllib.error.HTTPError) -> float | None:
    said = (refused.headers.get("Retry-After") or "").strip() if refused.headers else ""
    return float(said) if said.isdigit() else None
