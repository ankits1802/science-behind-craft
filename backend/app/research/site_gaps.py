from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from types import MappingProxyType
from typing import Annotated, Literal

from pydantic import Field

from .base import ContractModel
from .page_proposals import PageSubject

__all__ = [
    "EVIDENCE_MAX",
    "GAP_KINDS",
    "GAP_MEANINGS",
    "SITE_GAP_ACTION",
    "SITE_GAP_TARGET",
    "FiledGap",
    "SiteGap",
    "SiteGapRow",
]

SITE_GAP_ACTION = "site_gap.reported"
SITE_GAP_TARGET = "PageSubject"
EVIDENCE_MAX = 5
WANTED_MIN_CHARS = 10
TEXT_MAX_CHARS = 600
GAP_MEANINGS: Mapping[str, str] = MappingProxyType(
    {
        "KIND": "no component kind draws what the page needs",
        "TOOL": "no tool makes, places or reads it",
        "LIMIT": "a bound or an allowance stops it",
        "DRAWING": "the site draws a delivered part wrongly or not at all",
        "OTHER": "anything else the site could not do",
    }
)
GAP_KINDS = tuple(GAP_MEANINGS)

Text = Annotated[str, Field(min_length=1, max_length=TEXT_MAX_CHARS)]


class SiteGap(ContractModel):
    subject: PageSubject | None = None
    kind: Literal[*GAP_KINDS]
    wanted: str = Field(min_length=WANTED_MIN_CHARS, max_length=TEXT_MAX_CHARS)
    tried: Text | None = None
    evidence: list[Text] = Field(min_length=1, max_length=EVIDENCE_MAX)


class FiledGap(ContractModel):
    filed: bool
    kind: str
    message: str
    next_step: str


class SiteGapRow(ContractModel):
    filed_at: datetime
    kind: str
    subject: str | None
    wanted: str
    tried: str | None
    evidence: list[str]
    client: str | None
