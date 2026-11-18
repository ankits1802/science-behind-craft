from __future__ import annotations

from collections.abc import Mapping
from types import MappingProxyType
from typing import Any, Literal

from app.core.roles import STUDENT, role_value
from app.models.enums import AGE_BANDS, GENDERS, READING_STYLES

__all__ = [
    "AGE_BANDS",
    "AGE_BAND_LABELS",
    "GENDERS",
    "GENDER_LABELS",
    "READING_STYLES",
    "READING_STYLE_INSTRUCTIONS",
    "STYLED_PIECE_KINDS",
    "STYLE_LIMIT",
    "STYLE_OF_BAND",
    "AgeBand",
    "Gender",
    "ReadingStyle",
    "piece_style",
    "reading_style_for",
    "style_paragraph",
]

AgeBand = Literal[*AGE_BANDS]
Gender = Literal[*GENDERS]
ReadingStyle = Literal[*READING_STYLES]

AGE_BAND_LABELS: Mapping[str, str] = MappingProxyType(
    {"UNDER_14": "Under 14", "14_17": "14 to 17", "18_22": "18 to 22", "23_PLUS": "23 and over"}
)
GENDER_LABELS: Mapping[str, str] = MappingProxyType(
    {"WOMAN": "Woman", "MAN": "Man", "ANOTHER": "Another identity", "UNSAID": "Prefer not to say"}
)
STYLE_OF_BAND: Mapping[str, ReadingStyle | None] = MappingProxyType(
    {"UNDER_14": "CHILD", "14_17": "TEEN", "18_22": "UNDERGRADUATE", "23_PLUS": None}
)
STYLE_LIMIT = (
    "This changes only the wording: state the same facts, figures and citations you would for any reader, "
    "and follow every source rule above."
)
READING_STYLE_INSTRUCTIONS: Mapping[str, str] = MappingProxyType(
    {
        "CHILD": (
            "Reader: a school student under 14. Use everyday words and short sentences of about 12 words, "
            "never more than 18. The first time a scientific word appears, say what it means in the same "
            "sentence. Tell the process as a story of what the artisan's hands and materials do, step by "
            "step, warmly and plainly."
        ),
        "TEEN": (
            "Reader: a secondary-school student aged 14 to 17. Use clear words and sentences of at most 22 "
            "words. Name each scientific term and explain it once in plain words. Tell the process as a chain "
            "of causes and effects, step by step."
        ),
        "UNDERGRADUATE": (
            "Reader: a college student aged 18 to 22. Use the field's terms, each explained briefly the first "
            "time, and sentences of at most 28 words. Connect each step to the reason it works."
        ),
    }
)
STYLED_PIECE_KINDS = frozenset({"prose", "process_ladder"})


def reading_style_for(role: Any, student_profile: Any | None) -> ReadingStyle | None:
    if role_value(role) != STUDENT or student_profile is None:
        return None
    return STYLE_OF_BAND[student_profile.ageBand]


def style_paragraph(style: ReadingStyle | None) -> str | None:
    if style is None:
        return None
    return f"{READING_STYLE_INSTRUCTIONS[style]} {STYLE_LIMIT}"


def piece_style(kind: str, style: ReadingStyle | None) -> ReadingStyle | None:
    return style if kind in STYLED_PIECE_KINDS else None
