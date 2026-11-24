from __future__ import annotations

import uuid
from typing import Literal, Self

from pydantic import Field, model_validator

from app.models.enums import IMAGE_ORIGINS
from app.models.open_pictures import OPEN_CREDIT_CHARS

from .base import ContractModel, HttpsUrl, absent
from .blocks import ExplainerSentence, require_facts
from .image_contributions import (
    AI_GENERATED,
    GENERATOR_MAX_CHARS,
    IMAGE_TEXT_MAX_CHARS,
    OPEN_LICENCE,
    shown_label,
)
from .image_intake import AVIF, JPEG, PNG, SVG, WEBP
from .open_pictures import PHOTO_PREFIX

__all__ = [
    "CONTRIBUTED_CREDIT",
    "CONTRIBUTED_MIMES",
    "CONTRIBUTED_PATH",
    "CONTRIBUTED_PER_CHAPTER_MAX",
    "ContributedPlate",
    "contributed_credit",
    "contributed_key",
    "contributed_url",
]

CONTRIBUTED_CREDIT = "Contributed to KalaVigyan"
CONTRIBUTED_PATH = "/api/crafts/contributed/{id}"
CONTRIBUTED_MIMES = (PNG, JPEG, WEBP, AVIF, SVG)
CONTRIBUTED_PER_CHAPTER_MAX = 6
CONTRIBUTED_KEY_PREFIX = "contributed-"
CONTRIBUTED_KEY_HEX_CHARS = 12


def contributed_credit(origin: str, made_with: str | None) -> str:
    if origin == AI_GENERATED:
        return shown_label(origin, made_with)
    return CONTRIBUTED_CREDIT


def contributed_url(contribution_id: uuid.UUID) -> str:
    return CONTRIBUTED_PATH.format(id=contribution_id)


def contributed_key(contribution_id: uuid.UUID) -> str:
    return f"{CONTRIBUTED_KEY_PREFIX}{contribution_id.hex[:CONTRIBUTED_KEY_HEX_CHARS]}"


class ContributedPlate(ContractModel):
    contribution_id: uuid.UUID
    url: str = Field(pattern=r"^/api/crafts/contributed/[0-9a-f-]{36}$")
    mime: Literal[*CONTRIBUTED_MIMES]
    width: int = Field(ge=1)
    height: int = Field(ge=1)
    origin: Literal[*IMAGE_ORIGINS]
    made_with: str | None = Field(min_length=2, max_length=GENERATOR_MAX_CHARS)
    caption: str = Field(min_length=1, max_length=IMAGE_TEXT_MAX_CHARS)
    alt_text: str = Field(min_length=1, max_length=IMAGE_TEXT_MAX_CHARS)
    credit: str = Field(min_length=1, max_length=OPEN_CREDIT_CHARS)
    stage_id: uuid.UUID | None
    sentences: list[ExplainerSentence]
    source_url: HttpsUrl | None = Field(default=None, exclude_if=absent)

    @model_validator(mode="after")
    def _credited_as_its_origin_asks(self) -> Self:
        owner = f"contributed picture {self.contribution_id}"
        if self.url != contributed_url(self.contribution_id):
            raise ValueError(f"{owner} is served from its own address")
        if (self.origin == AI_GENERATED) != (self.made_with is not None):
            raise ValueError(f"{owner} names the tool it was made with exactly when an AI made it")
        if self.origin == OPEN_LICENCE:
            if self.source_url is None or not self.credit.startswith(PHOTO_PREFIX):
                raise ValueError(f"{owner} is credited to its author and licence, linked to its own page")
        elif self.source_url is not None or self.credit != contributed_credit(self.origin, self.made_with):
            raise ValueError(f"{owner} is credited {contributed_credit(self.origin, self.made_with)!r}")
        require_facts(owner, self.sentences)
        return self
