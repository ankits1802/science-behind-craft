from __future__ import annotations

from .base import ContractModel
from .page_proposals import PageSubject
from .review_queue_parts import RelatedFact
from .section_proposals import SectionCheck
from .vocabulary import Discipline

__all__ = ["ReviewedSentence", "SectionReview"]


class ReviewedSentence(ContractModel):
    text: str
    facts: list[RelatedFact]


class SectionReview(ContractModel):
    subject: PageSubject
    subject_name: str
    page_url: str
    field: Discipline
    proposed: list[ReviewedSentence]
    published: list[ReviewedSentence]
    published_version: int | None
    note: str | None
    task_key: str | None
    checks: list[SectionCheck]
    stale: str | None
