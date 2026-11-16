from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass

from app.core.errors import InvalidInput

__all__ = ["Box", "VideoFacts", "boxes", "video_facts", "without_audio"]

CONTAINERS = frozenset({b"moov", b"trak", b"mdia", b"minf", b"stbl"})
VIDEO_HANDLER = b"vide"
AUDIO_HANDLER = b"soun"
OFFSET_TABLES = {b"stco": 4, b"co64": 8}


@dataclass(frozen=True)
class Box:
    kind: bytes
    start: int
    header: int
    end: int

    @property
    def body(self) -> int:
        return self.start + self.header


@dataclass(frozen=True)
class VideoFacts:
    width: int
    height: int
    duration_seconds: float
    has_audio: bool


def boxes(data: bytes, start: int, end: int) -> list[Box]:
    found: list[Box] = []
    at = start
    while at < end:
        if end - at < 8:
            raise InvalidInput(f"MP4 box header cut short at byte {at}")
        size = int.from_bytes(data[at : at + 4])
        kind = bytes(data[at + 4 : at + 8])
        header = 8
        if size == 1:
            size, header = int.from_bytes(data[at + 8 : at + 16]), 16
        elif size == 0:
            size = end - at
        if size < header or at + size > end:
            raise InvalidInput(f"MP4 box {kind!r} at byte {at} overruns its parent")
        found.append(Box(kind, at, header, at + size))
        at += size
    return found


def video_facts(data: bytes) -> VideoFacts:
    moov = _moov(data)
    tracks = [(trak, _handler(data, trak)) for trak in _children(data, moov, b"trak")]
    video = [trak for trak, handler in tracks if handler == VIDEO_HANDLER]
    if len(video) != 1:
        raise InvalidInput(f"An MP4 needs exactly one video track, found {len(video)}")
    width, height = _dimensions(data, _child(data, video[0], b"tkhd"))
    return VideoFacts(
        width=width,
        height=height,
        duration_seconds=_track_seconds(data, video[0]),
        has_audio=any(handler == AUDIO_HANDLER for _, handler in tracks),
    )


def without_audio(data: bytes) -> bytes:
    moov = _moov(data)
    audio = [trak for trak in _children(data, moov, b"trak") if _handler(data, trak) == AUDIO_HANDLER]
    if not audio:
        return data
    removed = sum(trak.end - trak.start for trak in audio)
    patched = bytearray(data)
    if any(box.kind == b"mdat" and box.start > moov.start for box in boxes(data, 0, len(data))):
        for trak in _children(data, moov, b"trak"):
            if trak not in audio:
                _shift_offsets(data, patched, trak, -removed)
    kept = b"".join(
        bytes(patched[b.start : b.end]) for b in boxes(data, moov.body, moov.end) if b not in audio
    )
    header = _header(moov, moov.header + len(kept))
    return bytes(patched[: moov.start]) + header + kept + bytes(patched[moov.end :])


def _moov(data: bytes) -> Box:
    top = boxes(data, 0, len(data))
    if any(box.kind == b"moof" for box in top):
        raise InvalidInput("A fragmented MP4 is not accepted")
    found = [box for box in top if box.kind == b"moov"]
    if len(found) != 1:
        raise InvalidInput(f"An MP4 needs one moov box, found {len(found)}")
    return found[0]


def _children(data: bytes, parent: Box, kind: bytes) -> list[Box]:
    return [box for box in boxes(data, parent.body, parent.end) if box.kind == kind]


def _child(data: bytes, parent: Box, kind: bytes) -> Box:
    found = _children(data, parent, kind)
    if len(found) != 1:
        raise InvalidInput(f"MP4 {parent.kind!r} needs one {kind!r} box, found {len(found)}")
    return found[0]


def _path(data: bytes, parent: Box, *kinds: bytes) -> Box:
    box = parent
    for kind in kinds:
        box = _child(data, box, kind)
    return box


def _handler(data: bytes, trak: Box) -> bytes:
    hdlr = _path(data, trak, b"mdia", b"hdlr")
    return bytes(data[hdlr.body + 8 : hdlr.body + 12])


def _dimensions(data: bytes, tkhd: Box) -> tuple[int, int]:
    at = tkhd.body + (88 if data[tkhd.body] == 1 else 76)
    width = int.from_bytes(data[at : at + 4]) >> 16
    height = int.from_bytes(data[at + 4 : at + 8]) >> 16
    if width < 1 or height < 1:
        raise InvalidInput("The MP4 video track has no size")
    return width, height


def _track_seconds(data: bytes, trak: Box) -> float:
    mdhd = _path(data, trak, b"mdia", b"mdhd")
    if data[mdhd.body] == 1:
        timescale = int.from_bytes(data[mdhd.body + 20 : mdhd.body + 24])
        duration = int.from_bytes(data[mdhd.body + 24 : mdhd.body + 32])
    else:
        timescale = int.from_bytes(data[mdhd.body + 12 : mdhd.body + 16])
        duration = int.from_bytes(data[mdhd.body + 16 : mdhd.body + 20])
    if timescale < 1 or duration < 1:
        raise InvalidInput("The MP4 video track has no duration")
    return round(duration / timescale, 3)


def _shift_offsets(data: bytes, patched: bytearray, trak: Box, delta: int) -> None:
    stbl = _path(data, trak, b"mdia", b"minf", b"stbl")
    for table in boxes(data, stbl.body, stbl.end):
        width = OFFSET_TABLES.get(table.kind)
        if width is None:
            continue
        for at in _entries(patched, table, width):
            moved = int.from_bytes(patched[at : at + width]) + delta
            if moved < 0:
                raise InvalidInput("An MP4 chunk offset would fall before the file")
            patched[at : at + width] = moved.to_bytes(width)


def _entries(patched: bytearray, table: Box, width: int) -> Iterator[int]:
    count = int.from_bytes(patched[table.body + 4 : table.body + 8])
    first = table.body + 8
    if first + count * width > table.end:
        raise InvalidInput(f"MP4 {table.kind!r} lists more entries than it holds")
    return (first + index * width for index in range(count))


def _header(box: Box, size: int) -> bytes:
    if box.header == 16:
        return (1).to_bytes(4) + box.kind + size.to_bytes(8)
    if size >= 2**32:
        raise InvalidInput("The MP4 moov box grew past its header")
    return size.to_bytes(4) + box.kind
