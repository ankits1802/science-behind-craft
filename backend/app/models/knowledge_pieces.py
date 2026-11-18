import uuid
from datetime import datetime
from typing import Any

from pgvector.sqlalchemy import Vector
from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, Text, text
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, created_at, one_of, updated_at, uuid_pk
from app.models.crafts import EMBEDDING_DIMENSIONS
from app.models.enums import BLOCK_KINDS, DISCIPLINES, EXPLAINER_DEPTHS, READING_STYLES

TOPIC_KEY_COLUMN_CHARS = 200


class KnowledgePiece(Base):
    __tablename__ = "KnowledgePiece"

    id: Mapped[uuid.UUID] = uuid_pk()
    craftId: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("Craft.id", ondelete="CASCADE")
    )
    kind: Mapped[str] = mapped_column(String(32), nullable=False)
    facet: Mapped[str] = mapped_column(String(16), nullable=False)
    topicKey: Mapped[str] = mapped_column(String(TOPIC_KEY_COLUMN_CHARS), nullable=False)
    language: Mapped[str] = mapped_column(String(16), nullable=False)
    depth: Mapped[str] = mapped_column(String(16), nullable=False)
    readingStyle: Mapped[str | None] = mapped_column(String(16))
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    claimIds: Mapped[list[uuid.UUID]] = mapped_column(ARRAY(UUID(as_uuid=True)), nullable=False)
    sourceIds: Mapped[list[str]] = mapped_column(ARRAY(Text), nullable=False)
    contentHash: Mapped[str] = mapped_column(String(64), nullable=False)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(EMBEDDING_DIMENSIONS))
    createdFromAnswerId: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("Answer.id", ondelete="SET NULL")
    )
    staleSince: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    supersededById: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("KnowledgePiece.id", ondelete="SET NULL")
    )
    hiddenAt: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    hiddenById: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("User.id", ondelete="SET NULL")
    )
    createdAt: Mapped[datetime] = created_at()
    updatedAt: Mapped[datetime] = updated_at()

    __table_args__ = (
        CheckConstraint(one_of("kind", BLOCK_KINDS), name="kind"),
        CheckConstraint(one_of("facet", DISCIPLINES), name="facet"),
        CheckConstraint(one_of("depth", EXPLAINER_DEPTHS), name="depth"),
        CheckConstraint(
            '"readingStyle" IS NULL OR ' + one_of("readingStyle", READING_STYLES), name="readingStyle"
        ),
        CheckConstraint('cardinality("claimIds") > 0 AND cardinality("sourceIds") > 0', name="rests_on"),
        CheckConstraint('"hiddenById" IS NULL OR "hiddenAt" IS NOT NULL', name="hidden_by"),
        Index(None, "craftId", "facet", "topicKey"),
        Index("KnowledgePiece_claimIds_gin_idx", "claimIds", postgresql_using="gin"),
        Index(None, "createdFromAnswerId"),
        Index(None, "supersededById"),
        Index(None, "hiddenById"),
        Index(None, "contentHash"),
        Index(None, "staleSince", postgresql_where=text('"staleSince" IS NOT NULL')),
    )
