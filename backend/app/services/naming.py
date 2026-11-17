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
    "molecule_key",
    "narration_file_name",
    "narration_key",
    "place_field",
    "river_topology_file_name",
    "river_topology_key",
]

PORTAL = "KalaVigyan"
FILE_MAX = 150
SUBJECT_MAX = 40
MEDIA_PREFIX = "media"
NARRATION_FOLDER = "narration"
MOLECULE_FOLDER = "molecules"
RIVER_FOLDER = "rivers"
RIVER_TOPOLOGY_SUBJECT = "HydroRIVERS-1-0"
NARRATION_PARTS_MAX = 99
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
    return f"{MEDIA_PREFIX}/{owner_id}/{(token or uuid.uuid4()).hex}/{_one_file_name(leaf, 'media')}"


def narration_file_name(generated_at: datetime, part: int) -> str:
    if not 1 <= part <= NARRATION_PARTS_MAX:
        raise InvalidInput(f"Narration part {part} does not fit Part-NN")
    return file_name(
        entity="Explainer",
        what="Narration",
        ext="mp3",
        moment=generated_at,
        place=PlaceParts(),
        craft=None,
        subject=None,
        sequence=f"Part-{part:02d}",
    )


def narration_key(cache_id: str, leaf: str) -> str:
    if not _hex_digest(cache_id):
        raise InvalidInput("A narration key is filed under its 64-hex cache id")
    return f"{MEDIA_PREFIX}/{NARRATION_FOLDER}/{cache_id}/{_one_file_name(leaf, 'narration')}"


def molecule_key(pubchem_cid: int, leaf: str) -> str:
    if pubchem_cid < 1:
        raise InvalidInput("A molecule key is filed under its PubChem CID")
    return f"{MEDIA_PREFIX}/{MOLECULE_FOLDER}/{pubchem_cid}/{_one_file_name(leaf, 'molecule')}"


def river_topology_file_name(main_riv: int) -> str:
    if main_riv < 1:
        raise InvalidInput("A river topology is filed under its outlet reach id")
    return (
        "_".join((PORTAL, "Dataset", RIVER_TOPOLOGY_SUBJECT, "River-Topology", f"Basin-{main_riv}")) + ".json"
    )


def river_topology_key(edition: str, main_riv: int, sha256: str) -> str:
    if not edition or not edition.isascii() or not edition.replace("-", "").isalnum():
        raise InvalidInput("A river topology key is filed under the dataset's ASCII edition")
    if not _hex_digest(sha256):
        raise InvalidInput("A river topology key is filed under the 64-hex SHA-256 of its content")
    folder = f"{MEDIA_PREFIX}/{RIVER_FOLDER}/{edition}/{main_riv}/{sha256}"
    return f"{folder}/{river_topology_file_name(main_riv)}"


def _hex_digest(value: str) -> bool:
    return len(value) == 64 and all(ch in "0123456789abcdef" for ch in value)


def content_disposition(leaf: str, *, inline: bool) -> str:
    if not leaf.isascii() or '"' in leaf or "\\" in leaf:
        raise InvalidInput("A download name is ASCII without quotes")
    kind = "inline" if inline else "attachment"
    return f"{kind}; filename=\"{leaf}\"; filename*=UTF-8''{quote(leaf, safe='')}"


def _one_file_name(leaf: str, what: str) -> str:
    if not leaf or "/" in leaf or not leaf.isascii():
        raise InvalidInput(f"A {what} key ends in one ASCII file name")
    return leaf


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
