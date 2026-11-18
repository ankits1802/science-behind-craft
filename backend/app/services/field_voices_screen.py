from __future__ import annotations

import re
from collections.abc import Callable, Iterator
from typing import Any

from app.research.evidence import PERSONAL_DATA
from app.services.field_voices_feed import IMAGES

__all__ = ["FIELD_PERSONAL_DATA", "PortalScreen", "field_personal_data_in", "without_field_personal_data"]

FIELD_PERSONAL_DATA = {
    "email address": PERSONAL_DATA["email address"],
    "spoken email address": PERSONAL_DATA["spoken email address"],
    "Aadhaar-like number": re.compile(r"(?<!\d)\d{4}[ .-]?\d{4}[ .-]?\d{4}(?!\d)"),
    "phone-like number": PERSONAL_DATA["phone-like number"],
    "PAN-like code": re.compile(r"(?<![A-Za-z0-9])[A-Za-z]{5}\d{4}[A-Za-z](?![A-Za-z0-9])"),
    "voter ID-like code": re.compile(r"(?<![A-Za-z0-9])[A-Za-z]{3}\d{7}(?![A-Za-z0-9])"),
    "IFSC-like code": re.compile(r"(?<![A-Za-z0-9])[A-Za-z]{4}0[A-Za-z0-9]{6}(?![A-Za-z0-9])"),
}
EMAIL_KINDS = frozenset({"email address", "spoken email address"})


def field_personal_data_in(text: str) -> list[str]:
    return [label for label, pattern in FIELD_PERSONAL_DATA.items() if pattern.search(text)]


def without_field_personal_data(text: str) -> str:
    for label, pattern in FIELD_PERSONAL_DATA.items():
        text = pattern.sub(_replacement("[email]" if label in EMAIL_KINDS else "[number]"), text)
    return text


def _replacement(placeholder: str) -> Callable[[re.Match[str]], str]:
    def replace(found: re.Match[str]) -> str:
        return placeholder + (" " if found.group()[-1] in " -" else "")

    return replace


SPEAKER_LABEL = "Speaker {n}"
TRANSCRIPT_LABELS = (
    ("workshop", "title"),
    ("session", "title"),
    ("record", "name"),
    ("record", "localName"),
    ("stage", "rowLabel"),
)
IMAGE_LABELS = (("workshop", "title"),)
TOPIC_LABELS = ("sectionTitle", "question")
PERSON_LABELS = ("name", "localName")
PLACEMENT_LABELS = ("name", "localName", "englishName", "process")


class PortalScreen:
    def __init__(self) -> None:
        self.misses = 0

    def __call__(self, stream: str, item: dict[str, Any]) -> dict[str, Any]:
        for holder, key in self._labels(stream, item):
            self._null_label(holder, key)
        if stream == IMAGES:
            return item
        for position, speaker in enumerate(_dicts(item.get("speakers")), start=1):
            if _leaks(speaker.get("label")):
                speaker["label"] = SPEAKER_LABEL.format(n=position)
                self.misses += 1
        self._scrub_transcript(item.get("transcript"))
        return item

    def _labels(self, stream: str, item: dict[str, Any]) -> Iterator[tuple[dict[str, Any], str]]:
        for part, key in IMAGE_LABELS if stream == IMAGES else TRANSCRIPT_LABELS:
            holder = item.get(part)
            if isinstance(holder, dict):
                yield holder, key
        questionnaire = (item.get("session") or {}).get("questionnaire")
        if isinstance(questionnaire, dict):
            yield questionnaire, "title"
        for topic in _dicts(item.get("topics")):
            yield from ((topic, key) for key in TOPIC_LABELS)
        for person in _dicts(item.get("people")):
            yield from ((person, key) for key in PERSON_LABELS)
        if stream == IMAGES:
            yield item, "caption"
            yield from _placement_labels(item)

    def _null_label(self, holder: dict[str, Any], key: str) -> None:
        if _leaks(holder.get(key)):
            holder[key] = None
            self.misses += 1

    def _scrub_transcript(self, transcript: Any) -> None:
        if not isinstance(transcript, dict):
            return
        for segment in _dicts(transcript.get("segments")):
            for key in ("text", "english"):
                self._scrub(segment, key)
        english = transcript.get("english")
        if isinstance(english, dict):
            self._scrub(english, "text")

    def _scrub(self, holder: dict[str, Any], key: str) -> None:
        value = holder.get(key)
        if _leaks(value):
            holder[key] = without_field_personal_data(value)
            self.misses += 1


def _placement_labels(item: dict[str, Any]) -> Iterator[tuple[dict[str, Any], str]]:
    for placement in _dicts(item.get("belongsTo")):
        yield from ((placement, key) for key in PLACEMENT_LABELS)
        row = placement.get("row")
        if isinstance(row, dict):
            yield row, "label"


def _dicts(value: Any) -> list[dict[str, Any]]:
    return [entry for entry in value if isinstance(entry, dict)] if isinstance(value, list) else []


def _leaks(value: Any) -> bool:
    return isinstance(value, str) and bool(field_personal_data_in(value))
