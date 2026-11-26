import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, created_at, one_of, uuid_pk
from app.models.component_lifecycle import HOLD_SUBJECT_KINDS
from app.models.monograph_documents import SLUG_CHARS, SUBJECT_KIND_CHARS

__all__ = ["UPGRADE_SUBJECT_KINDS", "PageUpgrade"]

UPGRADE_SUBJECT_KINDS = HOLD_SUBJECT_KINDS


class PageUpgrade(Base):
    __tablename__ = "PageUpgrade"

    id: Mapped[uuid.UUID] = uuid_pk()
    subjectKind: Mapped[str] = mapped_column(String(SUBJECT_KIND_CHARS), nullable=False)
    subjectSlug: Mapped[str] = mapped_column(String(SLUG_CHARS), nullable=False)
    layoutVersion: Mapped[int] = mapped_column(Integer, nullable=False)
    lines: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    raisedAt: Mapped[datetime] = created_at()

    __table_args__ = (
        CheckConstraint(one_of("subjectKind", UPGRADE_SUBJECT_KINDS), name="subjectKind"),
        CheckConstraint('"layoutVersion" >= 1', name="layoutVersion"),
        CheckConstraint("jsonb_typeof(\"lines\") = 'array'", name="lines"),
        UniqueConstraint("subjectKind", "subjectSlug"),
    )
