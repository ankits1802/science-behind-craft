from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date

from app.research.field_voices import PORTAL_PUBLISHERS
from app.services.field_voices_items import FeedArea, FeedPerson, FeedWorkshop

__all__ = [
    "CREDIT_SEPARATOR",
    "Credited",
    "citation_line",
    "credit_line",
    "long_date",
    "month_year",
    "person_line",
    "recording_title",
    "span_locator",
    "workshop_line",
]

MONTHS = (
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
)
CREDIT_SEPARATOR = " · "
UNNAMED = {"ARTISAN": "An artisan", "DESIGNER": "A designer", "RESEARCHER": "A researcher"}
TITLE_LEADS = {"session": "Field interview", "stage": "Design workshop recording", "other": "Field recording"}


@dataclass(frozen=True)
class Credited:
    person: FeedPerson
    craft: str
    area: FeedArea | None


def long_date(day: date) -> str:
    return f"{day.day} {MONTHS[day.month - 1]} {day.year}"


def month_year(day: date) -> str:
    return f"{MONTHS[day.month - 1]} {day.year}"


def area_words(area: FeedArea | None) -> str | None:
    if area is None:
        return None
    parts = [part for part in (area.district, area.state) if part]
    return ", ".join(parts) or None


def person_line(credited: Credited) -> str:
    person = credited.person
    if person.name:
        return person.name
    place = area_words(person.area or credited.area)
    lead = f"{UNNAMED[person.kind]} of {credited.craft}"
    return f"{lead}, {place}" if place else lead


def workshop_line(workshop: FeedWorkshop | None, *, any_unnamed: bool, fallback_day: date) -> str | None:
    if workshop is None:
        return None
    if workshop.title and not any_unnamed:
        return workshop.title
    when = month_year(workshop.starts_on or fallback_day)
    place = area_words(workshop.area)
    return f"a workshop in {place}, {when}" if place else f"a workshop, {when}"


def recording_title(lead: str, workshop: str | None, area: FeedArea | None, day: date) -> str:
    where = workshop or area_words(area)
    parts = [TITLE_LEADS[lead], *([where] if where else []), long_date(day)]
    return ", ".join(parts)


def citation_line(speaker: str, *, day: date, workshop: str | None, portal: str, locator: str) -> str:
    parts = [speaker, f"interview recorded {long_date(day)}", *([workshop] if workshop else [])]
    return ", ".join([*parts, PORTAL_PUBLISHERS[portal], locator])


def credit_line(names: Sequence[str], *, workshop: str | None, day: date | None, portal: str) -> str:
    when = ", ".join(part for part in (workshop, long_date(day) if day else None) if part)
    parts = [", ".join(names) if names else None, when or None, PORTAL_PUBLISHERS[portal]]
    return CREDIT_SEPARATOR.join(part for part in parts if part)


def span_locator(start_ms: int | None, end_ms: int | None, *, first: int, last: int) -> str:
    if start_ms is None or end_ms is None:
        return f"paragraph {first}" if first == last else f"paragraphs {first}–{last}"
    return f"{_clock(start_ms)}–{_clock(end_ms)}"


def _clock(ms: int) -> str:
    seconds = ms // 1000
    hours, rest = divmod(seconds, 3600)
    minutes, secs = divmod(rest, 60)
    return f"{hours}:{minutes:02d}:{secs:02d}" if hours else f"{minutes}:{secs:02d}"
