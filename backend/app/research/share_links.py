from __future__ import annotations

from typing import Literal, Self

from pydantic import AwareDatetime, Field, model_validator

from .base import ContractModel

__all__ = [
    "SHARED_ANSWER_PAGE",
    "SHARED_LESSON_PAGE",
    "SHARE_SCHEMA_VERSION",
    "SHARE_TOKEN_PATTERN",
    "ShareLink",
    "shared_page",
]

SHARE_SCHEMA_VERSION = 1
SHARE_TOKEN_PATTERN = r"^[A-Za-z0-9_-]{22,64}$"
SHARED_ANSWER_PAGE = "/shared/answers"
SHARED_LESSON_PAGE = "/shared/lessons"
SHARED_PAGE_PATTERN = r"^/shared/(answers|lessons)/[A-Za-z0-9_-]{22,64}$"


class ShareLink(ContractModel):
    schema_version: Literal[1]
    shared: bool
    path: str | None = Field(pattern=SHARED_PAGE_PATTERN)
    shared_at: AwareDatetime | None

    @model_validator(mode="after")
    def _a_link_exactly_while_shared(self) -> Self:
        if (self.path is not None) != self.shared or (self.shared_at is not None) != self.shared:
            raise ValueError("a share link has a path and a time exactly while it is shared")
        return self


def shared_page(page: str, token: str | None) -> str | None:
    return None if token is None else f"{page}/{token}"
