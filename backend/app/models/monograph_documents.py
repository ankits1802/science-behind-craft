import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import CheckConstraint, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, created_at, uuid_pk

__all__ = ["DIGEST_CHARS", "SLUG_CHARS", "SUBJECT_KIND_CHARS", "MonographDocument"]

DIGEST_CHARS = 64
SLUG_CHARS = 200
SUBJECT_KIND_CHARS = 20


class MonographDocument(Base):
    __tablename__ = "MonographDocument"

    id: Mapped[uuid.UUID] = uuid_pk()
    subjectKind: Mapped[str] = mapped_column(String(SUBJECT_KIND_CHARS), nullable=False)
    subjectSlug: Mapped[str] = mapped_column(String(SLUG_CHARS), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    document: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    contentHash: Mapped[str] = mapped_column(String(DIGEST_CHARS), nullable=False)
    createdAt: Mapped[datetime] = created_at()

    __table_args__ = (
        CheckConstraint('"version" >= 1', name="version"),
        UniqueConstraint("subjectKind", "subjectSlug", "version"),
    )
