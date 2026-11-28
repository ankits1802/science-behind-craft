from __future__ import annotations

import uuid
from collections.abc import Sequence

from pydantic import AwareDatetime, Field

from app.research.article_sections import SectionSentence
from app.research.base import ContractModel
from app.research.section_proposals import SECTION_SENTENCES_MAX
from app.research.vocabulary import Discipline

__all__ = ["ReviewedSection", "one_section_a_field"]


class ReviewedSection(ContractModel):
    field: Discipline
    version: int = Field(ge=1)
    sentences: list[SectionSentence] = Field(min_length=1, max_length=SECTION_SENTENCES_MAX)
    reviewed_by: uuid.UUID | None = None
    reviewed_at: AwareDatetime

    @property
    def id(self) -> str:
        return self.field

    def claim_ids(self) -> list[uuid.UUID]:
        return list(dict.fromkeys(claim for sentence in self.sentences for claim in sentence.claim_ids))


def one_section_a_field(sections: Sequence[ReviewedSection]) -> str | None:
    fields = [section.field for section in sections]
    twice = sorted({field for field in fields if fields.count(field) > 1})
    return f"a dossier carries one reviewed section a field; {', '.join(twice)} has more" if twice else None
