from __future__ import annotations

from dataclasses import dataclass

FTYP = (20).to_bytes(4) + b"ftyp" + b"isom" + bytes(4) + b"isom"
VIDEO_SAMPLE = b"VVVV"
AUDIO_SAMPLE = b"AAAA"


def box(kind: bytes, payload: bytes) -> bytes:
    return (8 + len(payload)).to_bytes(4) + kind + payload


def full_box(kind: bytes, payload: bytes, *, version: int = 0) -> bytes:
    return box(kind, bytes([version, 0, 0, 0]) + payload)


def tkhd(width: int, height: int) -> bytes:
    payload = bytes(4 + 4) + (1).to_bytes(4) + bytes(4) + bytes(4) + bytes(8) + bytes(8) + bytes(36)
    return full_box(b"tkhd", payload + (width << 16).to_bytes(4) + (height << 16).to_bytes(4))


def mdhd(timescale: int, duration: int) -> bytes:
    return full_box(b"mdhd", bytes(8) + timescale.to_bytes(4) + duration.to_bytes(4) + bytes(4))


def hdlr(handler: bytes) -> bytes:
    return full_box(b"hdlr", bytes(4) + handler + bytes(12) + b"\x00")


def stco(offsets: list[int]) -> bytes:
    return full_box(b"stco", len(offsets).to_bytes(4) + b"".join(o.to_bytes(4) for o in offsets))


def trak(
    handler: bytes, offsets: list[int], *, size: tuple[int, int] = (1280, 720), seconds: float = 8.0
) -> bytes:
    timescale = 12_800
    stbl = box(b"stbl", stco(offsets))
    mdia = box(b"mdia", mdhd(timescale, int(seconds * timescale)) + hdlr(handler) + box(b"minf", stbl))
    return box(b"trak", tkhd(*size) + mdia)


@dataclass(frozen=True)
class Movie:
    data: bytes
    audio_trak_size: int
    video_offset: int


def movie(*, audio: bool = True, moov_first: bool = True, seconds: float = 8.0) -> Movie:
    mvhd = full_box(b"mvhd", bytes(96))
    mdat_payload = VIDEO_SAMPLE + AUDIO_SAMPLE
    placeholder = trak(b"vide", [0], seconds=seconds) + (trak(b"soun", [0]) if audio else b"")
    moov_size = 8 + len(mvhd) + len(placeholder)
    mdat_start = len(FTYP) + (moov_size if moov_first else 0)
    video_offset = mdat_start + 8
    tracks = trak(b"vide", [video_offset], seconds=seconds)
    audio_trak = trak(b"soun", [video_offset + 4]) if audio else b""
    moov = box(b"moov", mvhd + tracks + audio_trak)
    mdat = box(b"mdat", mdat_payload)
    body = FTYP + (moov + mdat if moov_first else mdat + moov)
    return Movie(body, len(audio_trak), video_offset)
