from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import Field, model_validator

from app.models.enums import IMAGE_CONTRIBUTION_STATUSES, IMAGE_ORIGINS

from .base import ContractModel
from .crafts import SLUG_MAX_CHARS

__all__ = [
    "AI_GENERATED",
    "IMAGE_TERMS_VERSION",
    "ORIGIN_LABELS",
    "ImageContributionStatus",
    "ImageContributionView",
    "ImageDeclaration",
    "ImageOrigin",
    "ImageQueue",
    "RejectDecision",
    "ReviewDecision",
    "shown_label",
]

IMAGE_TERMS_VERSION = "2026-11-19"
IMAGE_TERMS_VERSIONS = (IMAGE_TERMS_VERSION,)
IMAGE_TEXT_MAX_CHARS = 300
GENERATOR_MAX_CHARS = 120
PROMPT_MAX_CHARS = 4000
REVIEW_NOTE_MAX_CHARS = 500
CLAIMS_MAX = 20
AI_GENERATED = "AI_GENERATED"
ORIGIN_LABELS = {
    "PHOTOGRAPH": "Photograph",
    "DRAWING": "Drawing",
    AI_GENERATED: "Illustration, made with {tool}",
}

ImageOrigin = Literal[*IMAGE_ORIGINS]
ImageContributionStatus = Literal[*IMAGE_CONTRIBUTION_STATUSES]
TermsVersion = Literal[*IMAGE_TERMS_VERSIONS]


def shown_label(origin: str, generator: str | None) -> str:
    return ORIGIN_LABELS[origin].format(tool=generator or "")


class ImageDeclaration(ContractModel):
    craft_slug: str = Field(min_length=1, max_length=SLUG_MAX_CHARS)
    stage_id: uuid.UUID | None = None
    claim_ids: list[uuid.UUID] = Field(default_factory=list, max_length=CLAIMS_MAX)
    origin: ImageOrigin
    generator: str | None = Field(default=None, min_length=2, max_length=GENERATOR_MAX_CHARS)
    prompt: str | None = Field(default=None, min_length=1, max_length=PROMPT_MAX_CHARS)
    caption: str = Field(min_length=3, max_length=IMAGE_TEXT_MAX_CHARS)
    alt_text: str = Field(min_length=3, max_length=IMAGE_TEXT_MAX_CHARS)
    rights_confirmed: Literal[True]
    terms_version: TermsVersion

    @model_validator(mode="after")
    def _origin_is_declared(self) -> ImageDeclaration:
        if self.origin == AI_GENERATED and not (self.generator and self.prompt and self.claim_ids):
            raise ValueError("An AI-made image names its tool and model, its prompt and the facts it shows")
        if self.origin != AI_GENERATED and (self.generator or self.prompt):
            raise ValueError("Only an AI-made image carries a tool and a prompt")
        if len(set(self.claim_ids)) != len(self.claim_ids):
            raise ValueError("Each fact is named once")
        return self


class ReviewDecision(ContractModel):
    note: str | None = Field(default=None, min_length=1, max_length=REVIEW_NOTE_MAX_CHARS)


class RejectDecision(ContractModel):
    note: str = Field(min_length=3, max_length=REVIEW_NOTE_MAX_CHARS)


class ImageContributionView(ContractModel):
    id: uuid.UUID
    craft_slug: str
    craft_name: str
    stage_id: uuid.UUID | None
    claim_ids: list[uuid.UUID]
    origin: ImageOrigin
    label: str
    generator: str | None
    prompt: str | None
    caption: str
    alt_text: str
    status: ImageContributionStatus
    ai_marked: bool
    mime: str | None
    width: int | None
    height: int | None
    file_url: str | None
    created_at: datetime
    reviewed_at: datetime | None
    review_note: str | None


class ImageQueue(ContractModel):
    status: ImageContributionStatus
    items: list[ImageContributionView]
