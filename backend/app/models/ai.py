import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models import enums as e
from app.models.base import Base, created_at, updated_at, uuid_pk


class ManagedSecret(Base):
    __tablename__ = "ManagedSecret"

    id: Mapped[uuid.UUID] = uuid_pk()
    key: Mapped[str] = mapped_column(String(120), nullable=False, unique=True)
    valueEnc: Mapped[str] = mapped_column(Text, nullable=False)
    hint: Mapped[str | None] = mapped_column(String(16))
    description: Mapped[str | None] = mapped_column(Text)
    lastStatus: Mapped[str] = mapped_column(String(16), nullable=False, server_default="UNKNOWN")
    lastCheckedAt: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    lastError: Mapped[str | None] = mapped_column(Text)
    updatedById: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("User.id", ondelete="SET NULL")
    )
    createdAt: Mapped[datetime] = created_at()
    updatedAt: Mapped[datetime] = updated_at()

    __table_args__ = (Index(None, "updatedById"),)


class SecretTestResult(Base):
    __tablename__ = "SecretTestResult"

    id: Mapped[uuid.UUID] = uuid_pk()
    key: Mapped[str] = mapped_column(String(120), nullable=False, unique=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    checkedAt: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    error: Mapped[str | None] = mapped_column(Text)
    fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    createdAt: Mapped[datetime] = created_at()
    updatedAt: Mapped[datetime] = updated_at()


class Provider(Base):
    __tablename__ = "Provider"

    id: Mapped[uuid.UUID] = uuid_pk()
    name: Mapped[str] = mapped_column(e.AiProvider, nullable=False, unique=True)
    preset: Mapped[str] = mapped_column(String(40), nullable=False)
    kind: Mapped[str] = mapped_column(String(40), nullable=False)
    baseUrl: Mapped[str | None] = mapped_column(Text)
    apiKeySecretKey: Mapped[str] = mapped_column(String(120), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    maxConcurrency: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("4"))
    dataClass: Mapped[str] = mapped_column(e.ProviderDataClass, nullable=False, server_default="ANY")
    learned: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))
    extra: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))
    createdAt: Mapped[datetime] = created_at()
    updatedAt: Mapped[datetime] = updated_at()


class RoutePolicy(Base):
    __tablename__ = "RoutePolicy"

    id: Mapped[uuid.UUID] = uuid_pk()
    task: Mapped[str] = mapped_column(e.AiTask, nullable=False)
    ordinal: Mapped[int] = mapped_column(Integer, nullable=False)
    providerId: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("Provider.id", ondelete="CASCADE"), nullable=False
    )
    model: Mapped[str] = mapped_column(String(120), nullable=False)
    maxOutputTokens: Mapped[int | None] = mapped_column(Integer)
    temperature: Mapped[float | None] = mapped_column(Float)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    params: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))
    updatedById: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("User.id", ondelete="SET NULL")
    )
    createdAt: Mapped[datetime] = created_at()
    updatedAt: Mapped[datetime] = updated_at()

    __table_args__ = (UniqueConstraint("task", "ordinal"), Index(None, "providerId"))


class UsageEvent(Base):
    __tablename__ = "UsageEvent"

    id: Mapped[uuid.UUID] = uuid_pk()
    userId: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("User.id", ondelete="SET NULL")
    )
    role: Mapped[str | None] = mapped_column(e.UserRole)
    task: Mapped[str] = mapped_column(e.AiTask, nullable=False)
    provider: Mapped[str | None] = mapped_column(e.AiProvider)
    model: Mapped[str | None] = mapped_column(String(120))
    routeOrdinal: Mapped[int | None] = mapped_column(Integer)
    inputTokens: Mapped[int | None] = mapped_column(Integer)
    outputTokens: Mapped[int | None] = mapped_column(Integer)
    cachedTokens: Mapped[int | None] = mapped_column(Integer)
    units: Mapped[float | None] = mapped_column(Float)
    unit: Mapped[str | None] = mapped_column(String(16))
    estimatedCostUsd: Mapped[Decimal] = mapped_column(
        Numeric(10, 6), nullable=False, server_default=text("0")
    )
    costUsd: Mapped[Decimal] = mapped_column(Numeric(10, 6), nullable=False, server_default=text("0"))
    isMedia: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    latencyMs: Mapped[int | None] = mapped_column(Integer)
    requestId: Mapped[str | None] = mapped_column(String(64))
    outcome: Mapped[str] = mapped_column(e.UsageOutcome, nullable=False)
    errorKind: Mapped[str | None] = mapped_column(String(40))
    detail: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    settledAt: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    createdAt: Mapped[datetime] = created_at()
    updatedAt: Mapped[datetime] = updated_at()

    __table_args__ = (
        Index(None, "createdAt"),
        Index(None, "userId", "createdAt"),
        Index(None, "task", "createdAt"),
        Index(None, "outcome", "createdAt"),
        Index(None, "requestId"),
    )


class QuotaPolicy(Base):
    __tablename__ = "QuotaPolicy"

    id: Mapped[uuid.UUID] = uuid_pk()
    role: Mapped[str] = mapped_column(e.UserRole, nullable=False)
    resource: Mapped[str] = mapped_column(e.QuotaResource, nullable=False)
    perDay: Mapped[Decimal | None] = mapped_column(Numeric(12, 4))
    perMonth: Mapped[Decimal | None] = mapped_column(Numeric(12, 4))
    createdAt: Mapped[datetime] = created_at()
    updatedAt: Mapped[datetime] = updated_at()

    __table_args__ = (UniqueConstraint("role", "resource"),)


class QuotaLedger(Base):
    __tablename__ = "QuotaLedger"

    id: Mapped[uuid.UUID] = uuid_pk()
    userId: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("User.id", ondelete="SET NULL")
    )
    resource: Mapped[str] = mapped_column(e.QuotaResource, nullable=False)
    units: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    refType: Mapped[str | None] = mapped_column(String(60))
    refId: Mapped[str | None] = mapped_column(String(120))
    idempotencyKey: Mapped[str] = mapped_column(String(160), nullable=False, unique=True)
    createdAt: Mapped[datetime] = created_at()
    updatedAt: Mapped[datetime] = updated_at()

    __table_args__ = (Index(None, "userId", "resource", "createdAt"),)


class AppSetting(Base):
    __tablename__ = "AppSetting"

    id: Mapped[uuid.UUID] = uuid_pk()
    key: Mapped[str] = mapped_column(String(120), nullable=False, unique=True)
    value: Mapped[Any] = mapped_column(JSONB, nullable=False)
    updatedById: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("User.id", ondelete="SET NULL")
    )
    createdAt: Mapped[datetime] = created_at()
    updatedAt: Mapped[datetime] = updated_at()


class Job(Base):
    __tablename__ = "Job"

    id: Mapped[uuid.UUID] = uuid_pk()
    queue: Mapped[str] = mapped_column(String(40), nullable=False)
    kind: Mapped[str] = mapped_column(String(80), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))
    status: Mapped[str] = mapped_column(e.JobStatus, nullable=False, server_default="QUEUED")
    priority: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    maxAttempts: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("3"))
    runAfter: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    lockedAt: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    lockedBy: Mapped[str | None] = mapped_column(String(120))
    lastError: Mapped[str | None] = mapped_column(Text)
    idempotencyKey: Mapped[str | None] = mapped_column(String(160), unique=True)
    createdAt: Mapped[datetime] = created_at()
    updatedAt: Mapped[datetime] = updated_at()

    __table_args__ = (Index(None, "queue", "status", "runAfter"),)
