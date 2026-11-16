from __future__ import annotations

import unicodedata
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from urllib.parse import quote

from app.core.clock import INDIA_TZ
from app.core.errors import InvalidInput
from app.data.craft_text import to_latin

__all__ = [
    "FILE_MAX",
    "PORTAL",
    "SUBJECT_MAX",
    "MediaName",
    "PlaceParts",
    "content_disposition",
    "field",
    "file_name",
    "generated_media_file_name",
    "media_key",
    "place_field",
]

PORTAL = "KalaVigyan"
FILE_MAX = 150
SUBJECT_MAX = 40
MEDIA_PREFIX = "media"
MEDIA_NAMES = {
    "IMAGE": ("Generated-Image", "Image", "png"),
    "VIDEO": ("Generated-Video", "Video", "mp4"),
}
RESERVED_STEMS = frozenset(
    {"CON", "PRN", "AUX", "NUL", *(f"COM{i}" for i in range(1, 10)), *(f"LPT{i}" for i in range(1, 10))}
)
_ZERO_WIDTH = frozenset({"‌", "‍"})


@dataclass(frozen=True)
class PlaceParts:
    locality: str | None = None
    district: str | None = None
    state: str | None = None


@dataclass(frozen=True)
class MediaName:
    kind: str
    generated_at: datetime
    place: PlaceParts
    craft: str
    stage_name: str
    stage_ordinal: int


def field(value: str | None) -> str:
    return "-".join(_field_words(value))


def place_field(place: PlaceParts) -> str:
    return field(_place_text(place))


def file_name(
    *,
    entity: str,
    what: str,
    ext: str,
    moment: datetime,
    place: PlaceParts,
    craft: str | None,
    subject: str | None,
    sequence: str | None,
) -> str:
    local = _ist(moment)
    fixed = (PORTAL, field(entity), local.date().isoformat(), local.strftime("%H%M"))
    tail = (field(what), sequence)

    def render(place_words: list[str], craft_words: list[str], subject_words: list[str]) -> str:
        middle = ("-".join(place_words), "-".join(craft_words), "-".join(subject_words))
        stem = "_".join(part for part in (*fixed, *middle, *tail) if part)
        return f"{_guard(stem)}.{ext}"

    return _fit(render, _field_words(_place_text(place)), _field_words(craft), _field_words(subject))


def generated_media_file_name(name: MediaName) -> str:
    entity, what, ext = _media_parts(name.kind)
    if not 0 <= name.stage_ordinal <= 99:
        raise InvalidInput(f"Stage ordinal {name.stage_ordinal} does not fit Step-NN")
    return file_name(
        entity=entity,
        what=what,
        ext=ext,
        moment=name.generated_at,
        place=name.place,
        craft=name.craft,
        subject=_capped_subject(name.stage_name),
        sequence=f"Step-{name.stage_ordinal:02d}",
    )


def media_key(owner_id: uuid.UUID, leaf: str, *, token: uuid.UUID | None = None) -> str:
    if not leaf or "/" in leaf or not leaf.isascii():
        raise InvalidInput("A media key ends in one ASCII file name")
    return f"{MEDIA_PREFIX}/{owner_id}/{(token or uuid.uuid4()).hex}/{leaf}"


def content_disposition(leaf: str, *, inline: bool) -> str:
    if not leaf.isascii() or '"' in leaf or "\\" in leaf:
        raise InvalidInput("A download name is ASCII without quotes")
    kind = "inline" if inline else "attachment"
    return f"{kind}; filename=\"{leaf}\"; filename*=UTF-8''{quote(leaf, safe='')}"


def _media_parts(kind: str) -> tuple[str, str, str]:
    parts = MEDIA_NAMES.get(kind)
    if parts is None:
        raise InvalidInput(f"No media name for kind {kind!r}")
    return parts


def _capped_subject(stage_name: str) -> str:
    words = _field_words(stage_name)
    while len(words) > 1 and len("-".join(words)) > SUBJECT_MAX:
        words.pop()
    if words and len(words[0]) > SUBJECT_MAX:
        words[0] = words[0][:SUBJECT_MAX]
    return " ".join(words)


def _field_words(value: str | None) -> list[str]:
    text = to_latin(value or "")
    words = ["".join(ch for ch in word if ch.isascii() and ch.isalnum()) for word in _split_words(text)]
    return [_title_case(word) for word in words if word]


def _split_words(value: str) -> list[str]:
    words: list[str] = []
    current: list[str] = []
    for ch in unicodedata.normalize("NFC", value):
        if ch in _ZERO_WIDTH or unicodedata.category(ch)[0] in ("L", "M") or unicodedata.category(ch) == "Nd":
            current.append(ch)
        elif current:
            words.append("".join(current))
            current = []
    if current:
        words.append("".join(current))
    return words


def _title_case(word: str) -> str:
    if any(ch.isdigit() for ch in word):
        return word
    if 2 <= len(word) <= 3 and word.isalpha() and word.isupper():
        return word
    return word[0].upper() + word[1:].lower()


def _place_text(place: PlaceParts) -> str | None:
    locality = (place.locality or "").strip()
    district = (place.district or "").strip()
    if locality and district and field(locality).casefold() != field(district).casefold():
        return f"{locality} {district}"
    return locality or district or (place.state or "").strip() or None


def _ist(moment: datetime) -> datetime:
    if moment.tzinfo is None:
        raise InvalidInput("A name's time must carry its time zone")
    return moment.astimezone(INDIA_TZ)


def _guard(stem: str) -> str:
    return f"{stem}-File" if stem.upper() in RESERVED_STEMS else stem


def _fit(
    render: Callable[[list[str], list[str], list[str]], str],
    place: list[str],
    craft: list[str],
    subject: list[str],
) -> str:
    def too_long() -> bool:
        return len(render(place, craft, subject)) > FILE_MAX

    for words, floor in ((subject, 1), (craft, 1), (place, 1), (subject, 0), (craft, 0), (place, 0)):
        _shorten(words, floor, too_long)
    if too_long():
        raise InvalidInput("A file name cannot fit in 150 characters")
    return render(place, craft, subject)


def _shorten(words: list[str], floor: int, too_long: Callable[[], bool]) -> None:
    while too_long() and len(words) > floor:
        words.pop()
