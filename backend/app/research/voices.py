from __future__ import annotations

from typing import Literal, Self

from pydantic import Field, model_validator

from .base import ContractModel, PartialDate
from .citations import Citation
from .evidence import personal_data_in

__all__ = [
    "VOICE_ENGLISH_SOURCES",
    "VOICE_LANGUAGE_PATTERN",
    "VOICE_ORIGINS",
    "VOICE_QUOTE_MAX_CHARS",
    "VOICE_ROLES",
    "VoiceQuote",
    "VoiceSpeaker",
    "voice_personal_data",
]

VOICE_ORIGINS = ("DESIGNER", "FIELD_REPOSITORY", "KALAVIGYAN")
VOICE_ROLES = ("ARTISAN", "DESIGNER")
VOICE_ENGLISH_SOURCES = ("ORIGINAL", "MACHINE", "EDITED", "REVIEWED")
VOICE_QUOTE_MAX_CHARS = 600
VOICE_LANGUAGE_PATTERN = r"^(?:und|[a-z]{2,3}(?:-[A-Za-z0-9]{1,8})*)$"


class VoiceSpeaker(ContractModel):
    name: str | None = Field(default=None, min_length=1, max_length=300)
    line: str = Field(min_length=1, max_length=400)
    role: Literal[*VOICE_ROLES]
    years_in_craft: int | None = Field(default=None, ge=0, le=90)
    district: str | None = Field(default=None, min_length=1, max_length=200)
    state: str | None = Field(default=None, min_length=1, max_length=200)


class VoiceQuote(ContractModel):
    item_id: str = Field(min_length=3, max_length=200)
    origin: Literal[*VOICE_ORIGINS]
    speaker: VoiceSpeaker
    quote: str = Field(min_length=1, max_length=VOICE_QUOTE_MAX_CHARS)
    language: str = Field(pattern=VOICE_LANGUAGE_PATTERN)
    english: str | None = Field(default=None, min_length=1)
    english_source: Literal[*VOICE_ENGLISH_SOURCES] | None = None
    source_id: str = Field(min_length=1)
    locator: str = Field(min_length=1, max_length=120)
    workshop: str | None = Field(default=None, min_length=1, max_length=400)
    recorded_on: PartialDate
    corroborated_by: list[Citation] = Field(default_factory=list)

    @model_validator(mode="after")
    def _english_with_its_source_and_nothing_personal(self) -> Self:
        if (self.english is None) != (self.english_source is None):
            raise ValueError(f"quote {self.item_id}: english and englishSource come together")
        if voice_personal_data(self):
            raise ValueError(f"quote {self.item_id} never shows a phone, email or identity number")
        return self


def voice_personal_data(quote: VoiceQuote) -> list[str]:
    speaker = quote.speaker
    texts = [
        quote.quote,
        quote.english,
        speaker.name,
        speaker.line,
        speaker.district,
        speaker.state,
        quote.workshop,
    ]
    return [label for text in texts if text for label in personal_data_in(text)]
