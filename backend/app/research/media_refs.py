from __future__ import annotations

import uuid
from typing import Literal, Self

from pydantic import AwareDatetime, Field, model_validator

from app.models.enums import MEDIA_DISPLAYS

from .base import ContractModel, HttpsUrl
from .evidence import ADAPTER_NAME_PATTERN
from .licences import open_licence

__all__ = ["MEDIA_DISPLAYS", "MediaDisplay", "MediaRef"]

MediaDisplay = Literal[*MEDIA_DISPLAYS]


class MediaRef(ContractModel):
    id: uuid.UUID
    display: MediaDisplay
    provider: str = Field(pattern=ADAPTER_NAME_PATTERN)
    page_url: HttpsUrl
    image_url: HttpsUrl
    width: int | None = Field(ge=1)
    height: int | None = Field(ge=1)
    title: str = Field(min_length=1, max_length=300)
    alt: str = Field(min_length=1, max_length=300)
    author: str | None = Field(max_length=300)
    site: str = Field(min_length=1, max_length=300)
    credit: str | None = Field(max_length=300)
    licence: str | None = Field(max_length=200)
    licence_url: HttpsUrl | None
    source_id: str | None
    retrieved_at: AwareDatetime

    @model_validator(mode="after")
    def _inline_only_with_an_open_licence_and_its_author(self) -> Self:
        if (self.width is None) != (self.height is None):
            raise ValueError(f"media {self.id} gives both its width and height, or neither")
        if self.display == "INLINE":
            if not (open_licence(self.licence) or open_licence(self.licence_url)):
                raise ValueError(f"media {self.id} is shown inline only under an open licence")
            if not self.author:
                raise ValueError(f"media {self.id} is shown inline only with its author")
        return self
