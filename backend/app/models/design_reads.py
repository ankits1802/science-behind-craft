from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import CheckConstraint, Index, Numeric, String, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, created_at
from app.models.image_screens import MODEL_CHARS, PROVIDER_CHARS

__all__ = ["PICTURES_KEY_CHARS", "DesignReadCache"]

PICTURES_KEY_CHARS = 64


class DesignReadCache(Base):
    __tablename__ = "DesignReadCache"

    picturesKey: Mapped[str] = mapped_column(String(PICTURES_KEY_CHARS), primary_key=True)
    reading: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    provider: Mapped[str] = mapped_column(String(PROVIDER_CHARS), nullable=False)
    model: Mapped[str] = mapped_column(String(MODEL_CHARS), nullable=False)
    costUsd: Mapped[Decimal] = mapped_column(Numeric(12, 6), nullable=False, server_default=text("0"))
    createdAt: Mapped[datetime] = created_at()

    __table_args__ = (
        CheckConstraint(f'char_length("picturesKey") = {PICTURES_KEY_CHARS}', name="picturesKey"),
        CheckConstraint("jsonb_typeof(\"reading\") = 'object'", name="reading"),
        CheckConstraint('"costUsd" >= 0', name="cost"),
        Index(None, "createdAt"),
    )
