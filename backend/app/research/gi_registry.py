from __future__ import annotations

import re
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, fields, replace

from .stated_dates import first_day_date

__all__ = [
    "IMITATION_SOURCE_KINDS",
    "MARKET_PREFILTER_WORDS",
    "REGISTRY_SOURCE_KINDS",
    "GiFields",
    "gi_fields",
    "gi_status_name",
    "merged_fields",
    "names_registry",
    "states_imitation",
]

REGISTRY_SOURCE_KINDS = ("GI_JOURNAL", "GOVERNMENT_REPORT")
IMITATION_SOURCE_KINDS = ("GI_JOURNAL",)
FIELD_WINDOW_CHARS = 80
PROPRIETOR_CHARS = (3, 150)
LABEL_GAP = r"\s*[:|\-–]*\s*"
NUMBERED = r"(?:\s+(?:number|no\.?))?"
APPLICATION = re.compile(rf"(?<!logo\s)\bapplication{NUMBERED}{LABEL_GAP}(?P<v>\d+)(?![-/.]\d)", re.I)
CERTIFICATE = re.compile(rf"\bcertificate{NUMBERED}{LABEL_GAP}(?P<v>\d+)(?![-/.]\d)", re.I)
JOURNAL = re.compile(rf"\bjournal(?:\s+(?:number|no\.?|issue))?{LABEL_GAP}(?P<v>\d+)(?![-/.]\d)", re.I)
USERS = re.compile(r"(?<![\d,])(?P<v>\d+)\s+authori[sz]ed\s+users?\b", re.I)
FILED = re.compile(r"\b(?:fil(?:ed|ing)|application\s+date|date\s+of\s+application)\b", re.I)
FILED_STOP = re.compile(r"\b(?:certificate|journal|registered|registration|valid|availability)\b", re.I)
REGISTERED_ON = re.compile(
    r"\b(?:certificate|registered\s+on|date\s+of\s+registration|registration\s+date)\b", re.I
)
REGISTERED_STOP = re.compile(r"\b(?:fil(?:ed|ing)|journal|valid|availability|application)\b", re.I)
PROPRIETOR = re.compile(
    r"\b(?:applicant\s+name|name\s+of\s+the\s+applicant)\s*[:|]*\s*(?P<v>[^|(\n]+?)"
    r"\s*(?=\(|\||\bapplicant\s+address\b|\s[A-Z]\)\s|$)",
    re.I,
)
LEADING_ARTICLE = re.compile(r"^the\s+", re.I)
REGISTRY_WORDS = re.compile(
    r"\b(?:GI|G\.I\.|geographical\s+indications?|application|certificate|journal|registered|registration)\b",
    re.I,
)
LOGO = re.compile(r"\blogo\b", re.I)
REGISTERED_WORDS = re.compile(r"\bregistered\b", re.I)
WITHDRAWN_WORDS = re.compile(r"\b(?:withdrawn|abandoned)\b", re.I)
IMITATION_WORDS = re.compile(
    r"\b(?:imitat\w*|fakes?|faked|counterfeit\w*|spurious|knock-?offs?|pass(?:ed|ing|es)?\s+off|"
    r"screen[- ]?print\w*|machine[- ]made|power[- ]?looms?|mill[- ]made)\b",
    re.I,
)
MARKET_PREFILTER_WORDS = (
    "geographical indication",
    "application",
    "certificate",
    "journal",
    "registered",
    "registration",
    "imitat",
    "fake",
    "counterfeit",
    "spurious",
    "knock",
    " off",
    "screen",
    "machine",
    "loom",
    "mill",
)


@dataclass(frozen=True)
class GiFields:
    application_number: str | None = None
    certificate_number: str | None = None
    filed_on: str | None = None
    registered_on: str | None = None
    journal_issue: str | None = None
    proprietors: tuple[str, ...] = ()
    authorised_user_count: int | None = None

    def stated(self) -> bool:
        return any(getattr(self, part.name) not in (None, ()) for part in fields(self))


def names_registry(text: str) -> bool:
    return REGISTRY_WORDS.search(text) is not None and LOGO.search(text) is None


def states_imitation(text: str) -> bool:
    return IMITATION_WORDS.search(text) is not None


def gi_fields(texts: Sequence[str]) -> GiFields | None:
    return merged_fields(_fields_in(text) for text in texts)


def merged_fields(found: Iterable[GiFields]) -> GiFields | None:
    every = list(found)
    merged = GiFields()
    for part in fields(GiFields):
        if part.name == "proprietors":
            continue
        values = {getattr(each, part.name) for each in every} - {None}
        if len(values) > 1:
            return None
        if values:
            merged = replace(merged, **{part.name: values.pop()})
    names: dict[str, str] = {}
    for name in (name for each in every for name in each.proprietors):
        names.setdefault(name.casefold(), name)
    return replace(merged, proprietors=tuple(names.values()))


def gi_status_name(gi: GiFields, texts: Sequence[str]) -> str | None:
    words = " ".join(texts)
    registered = gi.registered_on is not None or gi.certificate_number is not None
    if WITHDRAWN_WORDS.search(words):
        return "WITHDRAWN" if gi.application_number and not registered else None
    if registered:
        return "REGISTERED"
    if REGISTERED_WORDS.search(words):
        return None
    return "APPLIED" if gi.application_number or gi.filed_on else None


def _fields_in(text: str) -> GiFields:
    users = _first(USERS, text)
    return GiFields(
        application_number=_first(APPLICATION, text),
        certificate_number=_first(CERTIFICATE, text),
        filed_on=_date_after(FILED, FILED_STOP, text),
        registered_on=_date_after(REGISTERED_ON, REGISTERED_STOP, text),
        journal_issue=_first(JOURNAL, text),
        proprietors=tuple(_proprietors(text)),
        authorised_user_count=None if users is None else int(users),
    )


def _first(pattern: re.Pattern[str], text: str) -> str | None:
    values = {match.group("v") for match in pattern.finditer(text)}
    return values.pop() if len(values) == 1 else None


def _date_after(trigger: re.Pattern[str], stop: re.Pattern[str], text: str) -> str | None:
    values = set()
    for match in trigger.finditer(text):
        window = text[match.end() : match.end() + FIELD_WINDOW_CHARS]
        cut = stop.search(window)
        found = first_day_date(window[: cut.start()] if cut else window)
        if found is not None:
            values.add(found)
    return values.pop() if len(values) == 1 else None


def _proprietors(text: str) -> list[str]:
    names = []
    for match in PROPRIETOR.finditer(text):
        name = LEADING_ARTICLE.sub("", match.group("v").strip(" ,.;:"))
        if PROPRIETOR_CHARS[0] <= len(name) <= PROPRIETOR_CHARS[1]:
            names.append(name)
    return names
