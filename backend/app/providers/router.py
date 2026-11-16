from __future__ import annotations

import asyncio
import logging
import time
import uuid
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import case, func, select, text, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.errors import STOP_KINDS, AppError
from app.core.logging import current_request_id
from app.models import ManagedSecret, Provider, RoutePolicy, SecretTestResult, UsageEvent
from app.services import app_settings, managed_secrets
from app.services.ai_providers import (
    MEDIA_TASKS,
    PUBLIC_TEXT_TASKS,
    AiTask,
    model_for,
    supports,
    task_of,
)

from . import budget
from .base import Adapter, ChatRequest, ChatResult, ProviderError
from .registry import build_adapter, merge_learned

logger = logging.getLogger(__name__)

BUDGET_LOCK_KEY = 0x4B565F4255444754
RETRY_AFTER_CAP_SECONDS = 2.0
DEFAULT_MAX_OUTPUT_TOKENS = 4096
DEGRADABLE_TASKS = frozenset(
    {AiTask.COMPOSE, AiTask.EXTRACT, AiTask.VOICE_TURN, AiTask.PLAN, AiTask.WEB_READ}
)
EMBED_DIMENSIONS = 1536


@dataclass(frozen=True)
class Principal:
    user_id: uuid.UUID | None = None
    role: str | None = None


@dataclass(frozen=True)
class RouteChoice:
    ordinal: int
    provider: str
    provider_id: uuid.UUID | None
    preset: str
    kind: str
    base_url: str | None
    key_name: str
    model: str
    max_output_tokens: int | None = None
    temperature: float | None = None
    max_concurrency: int = 4
    data_class: str = "ANY"
    learned: dict[str, list[str]] = field(default_factory=dict)
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass
class RouterResult:
    task: str
    provider: str
    model: str
    ordinal: int
    usage_event_id: uuid.UUID
    cost_usd: Decimal
    degraded: bool
    attempts: list[dict[str, Any]]
    text: str = ""
    embeddings: list[list[float]] | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    meta: dict[str, Any] = field(default_factory=dict)


class RouterError(AppError):
    def __init__(
        self,
        kind: str,
        message: str,
        *,
        reason: str | None = None,
        attempts: list[dict[str, Any]] | None = None,
    ) -> None:
        super().__init__(message)
        self.kind = kind
        self.message = message
        self.reason = reason
        self.attempts = attempts or []


def route_allowed(choice: RouteChoice, task: AiTask) -> bool:
    if choice.data_class == "PUBLIC_TEXT_ONLY" and task not in PUBLIC_TEXT_TASKS:
        return False
    return supports(choice.provider, choice.model, task)


def estimate_for(
    choice: RouteChoice,
    task: AiTask,
    *,
    prompt_tokens: int,
    max_tokens: int,
    units: float | None,
    overrides: dict[str, Any] | None,
) -> Decimal:
    model = model_for(choice.provider, choice.model)
    if task in MEDIA_TASKS:
        return budget.unit_cost(model, units if units is not None else 1.0, overrides)
    output = 0 if task == AiTask.EMBED else max_tokens
    return budget.token_cost(model, input_tokens=prompt_tokens, output_tokens=output, overrides=overrides)


def order_routes(
    task: AiTask,
    routes: Sequence[RouteChoice],
    *,
    degrade: bool,
    estimate: Callable[[RouteChoice], Decimal],
) -> list[RouteChoice]:
    usable = sorted((r for r in routes if route_allowed(r, task)), key=lambda r: r.ordinal)
    if degrade and task in DEGRADABLE_TASKS:
        usable = sorted(usable, key=lambda r: (estimate(r), r.ordinal))
    return usable


_semaphores: dict[str, asyncio.Semaphore] = {}


def _semaphore(choice: RouteChoice) -> asyncio.Semaphore:
    found = _semaphores.get(choice.provider)
    if found is None:
        found = asyncio.Semaphore(max(1, choice.max_concurrency))
        _semaphores[choice.provider] = found
    return found


async def load_routes(session: AsyncSession, task: AiTask) -> list[RouteChoice]:
    rows = (
        await session.execute(
            select(RoutePolicy, Provider)
            .join(Provider, Provider.id == RoutePolicy.providerId)
            .where(RoutePolicy.task == task.value, RoutePolicy.enabled.is_(True), Provider.enabled.is_(True))
            .order_by(RoutePolicy.ordinal)
        )
    ).all()
    return [
        RouteChoice(
            ordinal=route.ordinal,
            provider=provider.name,
            provider_id=provider.id,
            preset=provider.preset,
            kind=provider.kind,
            base_url=provider.baseUrl,
            key_name=provider.apiKeySecretKey,
            model=route.model,
            max_output_tokens=route.maxOutputTokens,
            temperature=route.temperature,
            max_concurrency=provider.maxConcurrency,
            data_class=provider.dataClass,
            learned=dict(provider.learned or {}),
            extra=dict(provider.extra or {}),
        )
        for route, provider in rows
    ]


def _spend_sum() -> Any:
    fresh_cutoff = func.now() - text(f"interval '{int(budget.RESERVATION_TTL.total_seconds())} seconds'")
    amount = case(
        (
            UsageEvent.outcome == "RESERVED",
            case((UsageEvent.createdAt > fresh_cutoff, UsageEvent.estimatedCostUsd), else_=Decimal(0)),
        ),
        else_=UsageEvent.costUsd,
    )
    return func.coalesce(func.sum(amount), 0)


async def current_spend(
    session: AsyncSession, principal: Principal, now: datetime | None = None
) -> budget.SpendState:
    month_from = budget.month_start(now)
    month_total = (
        await session.execute(select(_spend_sum()).where(UsageEvent.createdAt >= month_from))
    ).scalar_one()
    media_total = (
        await session.execute(
            select(_spend_sum()).where(UsageEvent.createdAt >= month_from, UsageEvent.isMedia.is_(True))
        )
    ).scalar_one()
    user_day = Decimal(0)
    if principal.user_id is not None:
        user_day = (
            await session.execute(
                select(_spend_sum()).where(
                    UsageEvent.createdAt >= budget.day_start(now), UsageEvent.userId == principal.user_id
                )
            )
        ).scalar_one()
    return budget.SpendState(
        month_usd=budget.usd(month_total),
        media_month_usd=budget.usd(media_total),
        user_day_usd=budget.usd(user_day),
    )


async def tagged_spend(session: AsyncSession, *, request_id_prefix: str, since: datetime) -> Decimal:
    if not request_id_prefix:
        raise ValueError("A tagged spend needs a request id prefix")
    escaped = request_id_prefix.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    total = (
        await session.execute(
            select(_spend_sum()).where(
                UsageEvent.createdAt >= since,
                UsageEvent.requestId.like(f"{escaped}%", escape="\\"),
            )
        )
    ).scalar_one()
    return budget.usd(total)


async def reserve(
    session: AsyncSession,
    *,
    task: AiTask,
    choice: RouteChoice | None,
    principal: Principal,
    estimate_usd: Decimal,
    request_budget_usd: Decimal | None = None,
    units: float | None = None,
) -> tuple[uuid.UUID, budget.BudgetDecision]:
    await session.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": BUDGET_LOCK_KEY})
    settings_values = await app_settings.load_all(session)
    ceilings = budget.Ceilings.from_settings(settings_values)
    spend = await current_spend(session, principal)
    is_media = task in MEDIA_TASKS
    decision = budget.evaluate(
        ceilings,
        spend,
        estimate_usd=estimate_usd,
        is_media=is_media,
        role=principal.role,
        request_budget_usd=request_budget_usd,
    )
    event = UsageEvent(
        userId=principal.user_id,
        role=principal.role,
        task=task.value,
        provider=choice.provider if choice else None,
        model=choice.model if choice else None,
        routeOrdinal=choice.ordinal if choice else None,
        estimatedCostUsd=estimate_usd if decision.allowed else Decimal(0),
        costUsd=Decimal(0),
        isMedia=is_media,
        units=units,
        requestId=current_request_id(),
        outcome="RESERVED" if decision.allowed else "REFUSED_CEILING",
        errorKind=None if decision.allowed else decision.reason,
        settledAt=None if decision.allowed else datetime.now(UTC),
    )
    session.add(event)
    await session.flush()
    await session.commit()
    return event.id, decision


async def settle(
    session: AsyncSession,
    event_id: uuid.UUID,
    *,
    outcome: str,
    cost_usd: Decimal = Decimal(0),
    input_tokens: int | None = None,
    output_tokens: int | None = None,
    cached_tokens: int | None = None,
    latency_ms: int | None = None,
    error_kind: str | None = None,
    detail: dict[str, Any] | None = None,
    units: float | None = None,
    unit: str | None = None,
) -> None:
    values: dict[str, Any] = {
        "outcome": outcome,
        "costUsd": cost_usd,
        "inputTokens": input_tokens,
        "outputTokens": output_tokens,
        "cachedTokens": cached_tokens,
        "latencyMs": latency_ms,
        "errorKind": error_kind,
        "detail": detail,
        "settledAt": datetime.now(UTC),
    }
    if units is not None:
        values["units"] = units
    if unit is not None:
        values["unit"] = unit
    await session.execute(update(UsageEvent).where(UsageEvent.id == event_id).values(**values))
    await session.commit()


async def _mark_key_failed(session: AsyncSession, key_name: str, value: str | None, message: str) -> None:
    now = datetime.now(UTC)
    result = await session.execute(
        update(ManagedSecret)
        .where(ManagedSecret.key == key_name)
        .values(lastStatus=managed_secrets.STATUS_FAILED, lastCheckedAt=now, lastError=message[:500])
    )
    if not result.rowcount and value:
        payload = {
            "status": managed_secrets.STATUS_FAILED,
            "checkedAt": now,
            "error": message[:500],
            "fingerprint": managed_secrets.fingerprint(value),
        }
        await session.execute(
            insert(SecretTestResult)
            .values(key=key_name, **payload)
            .on_conflict_do_update(index_elements=[SecretTestResult.key], set_=payload)
        )
    await session.commit()
    managed_secrets.invalidate()


async def _persist_learned(session: AsyncSession, choice: RouteChoice, adapter: Adapter) -> None:
    if not adapter.learned_changed or choice.provider_id is None:
        return
    row = await session.get(Provider, choice.provider_id, with_for_update=True)
    if row is not None:
        row.learned = merge_learned(row.learned, adapter.learned)
        await session.commit()


@dataclass
class _CallOutcome:
    text: str = ""
    embeddings: list[list[float]] | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    cached_tokens: int | None = None
    latency_ms: int = 0
    meta: dict[str, Any] = field(default_factory=dict)


async def _call(
    adapter: Adapter,
    task: AiTask,
    choice: RouteChoice,
    *,
    system: str,
    user: str,
    json_schema: dict | None,
    max_tokens: int,
    temperature: float | None,
    texts: list[str] | None,
) -> _CallOutcome:
    if task == AiTask.EMBED:
        started = time.perf_counter()
        vectors = await adapter.embed(texts or [], choice.model, dimensions=EMBED_DIMENSIONS)
        latency = int((time.perf_counter() - started) * 1000)
        tokens = sum(budget.estimate_tokens(t) for t in texts or [])
        return _CallOutcome(
            embeddings=vectors,
            input_tokens=tokens,
            output_tokens=0,
            latency_ms=latency,
            meta={"estimatedTokens": True},
        )
    result: ChatResult = await adapter.chat(
        ChatRequest(
            model=choice.model,
            system=system,
            user=user,
            max_tokens=max_tokens,
            temperature=temperature,
            json_schema=json_schema,
        )
    )
    return _CallOutcome(
        text=result.text,
        input_tokens=result.input_tokens,
        output_tokens=result.output_tokens,
        cached_tokens=result.cached_input_tokens,
        latency_ms=result.latency_ms,
        meta=result.meta,
    )


async def run(
    task: AiTask | str,
    *,
    system: str = "",
    user: str = "",
    json_schema: dict | None = None,
    max_tokens: int | None = None,
    temperature: float | None = None,
    texts: list[str] | None = None,
    principal: Principal | None = None,
    request_budget_usd: Decimal | None = None,
    session_factory: async_sessionmaker[AsyncSession] | None = None,
) -> RouterResult:
    resolved = task_of(task)
    if resolved is None:
        raise RouterError("unsupported", f"Unknown task {task!r}")
    if resolved in MEDIA_TASKS:
        raise RouterError("unsupported", "Media tasks reserve and settle through reserve() and settle()")
    if resolved == AiTask.EMBED and not texts:
        raise RouterError("bad_request", "Embedding needs texts")
    if session_factory is None:
        from app.core.db import sessionmaker

        session_factory = sessionmaker()
    who = principal or Principal()
    prompt_text = "\n".join(texts) if resolved == AiTask.EMBED and texts else f"{system}\n{user}"
    prompt_tokens = budget.estimate_tokens(prompt_text)

    async with session_factory() as session:
        routes = await load_routes(session, resolved)
        settings_values = await app_settings.load_all(session)
        overrides = settings_values.get(app_settings.MODEL_PRICES) or {}
        ceilings = budget.Ceilings.from_settings(settings_values)
        spend = await current_spend(session, who)
        await managed_secrets.refresh_if_stale(session)

    degrade = budget.month_fraction(ceilings, spend) >= ceilings.degrade_at

    def output_cap(choice: RouteChoice) -> int:
        return max_tokens or choice.max_output_tokens or DEFAULT_MAX_OUTPUT_TOKENS

    def estimate(choice: RouteChoice) -> Decimal:
        return estimate_for(
            choice,
            resolved,
            prompt_tokens=prompt_tokens,
            max_tokens=output_cap(choice),
            units=None,
            overrides=overrides,
        )

    ordered = order_routes(resolved, routes, degrade=degrade, estimate=estimate)
    if not ordered:
        raise RouterError("no_route", f"No enabled route can run {resolved.value}")

    attempts: list[dict[str, Any]] = []
    for choice in ordered:
        estimate_usd = estimate(choice)
        async with session_factory() as session:
            event_id, decision = await reserve(
                session,
                task=resolved,
                choice=choice,
                principal=who,
                estimate_usd=estimate_usd,
                request_budget_usd=request_budget_usd,
            )
        if not decision.allowed:
            raise RouterError(
                "ceiling", decision.message or "Budget reached", reason=decision.reason, attempts=attempts
            )
        key_value = managed_secrets.peek_secret(choice.key_name)
        outcome: _CallOutcome | None = None
        failure: ProviderError | None = None
        adapter: Adapter | None = None
        for retry in range(2):
            try:
                adapter = build_adapter(
                    preset=choice.preset,
                    kind=choice.kind,
                    api_key=key_value,
                    api_key_name=choice.key_name,
                    base_url=choice.base_url,
                    extra=choice.extra,
                    learned=choice.learned,
                )
                async with _semaphore(choice):
                    outcome = await _call(
                        adapter,
                        resolved,
                        choice,
                        system=system,
                        user=user,
                        json_schema=json_schema,
                        max_tokens=output_cap(choice),
                        temperature=temperature if temperature is not None else choice.temperature,
                        texts=texts,
                    )
                failure = None
                break
            except ProviderError as exc:
                failure = exc
                wait = exc.retry_after
                if (
                    retry == 0
                    and exc.kind in {"rate_limit", "unavailable"}
                    and wait is not None
                    and wait <= RETRY_AFTER_CAP_SECONDS
                ):
                    await asyncio.sleep(wait)
                    continue
                break
            finally:
                if adapter is not None:
                    try:
                        await adapter.aclose()
                    except Exception:
                        logger.debug("adapter close failed", exc_info=True)
        async with session_factory() as session:
            if adapter is not None:
                await _persist_learned(session, choice, adapter)
            if outcome is not None:
                model = model_for(choice.provider, choice.model)
                cost = budget.token_cost(
                    model,
                    input_tokens=outcome.input_tokens,
                    output_tokens=outcome.output_tokens,
                    cached_tokens=outcome.cached_tokens,
                    overrides=overrides,
                )
                await settle(
                    session,
                    event_id,
                    outcome="OK",
                    cost_usd=cost,
                    input_tokens=outcome.input_tokens,
                    output_tokens=outcome.output_tokens,
                    cached_tokens=outcome.cached_tokens,
                    latency_ms=outcome.latency_ms,
                    detail={"servedModel": outcome.meta.get("served_model"), "degraded": degrade},
                )
                attempts.append({"provider": choice.provider, "model": choice.model, "outcome": "OK"})
                return RouterResult(
                    task=resolved.value,
                    provider=choice.provider,
                    model=choice.model,
                    ordinal=choice.ordinal,
                    usage_event_id=event_id,
                    cost_usd=cost,
                    degraded=degrade,
                    attempts=attempts,
                    text=outcome.text,
                    embeddings=outcome.embeddings,
                    input_tokens=outcome.input_tokens,
                    output_tokens=outcome.output_tokens,
                    meta=outcome.meta,
                )
            assert failure is not None
            stopped = failure.kind in STOP_KINDS
            await settle(
                session,
                event_id,
                outcome="REFUSED_PROVIDER" if failure.kind == "refusal" else "ERROR",
                error_kind=failure.kind,
                detail={"status": failure.status},
            )
            if failure.kind == "auth":
                await _mark_key_failed(session, choice.key_name, key_value, str(failure))
        attempts.append({"provider": choice.provider, "model": choice.model, "outcome": failure.kind})
        logger.warning(
            "route failed",
            extra={
                "task": resolved.value,
                "provider": choice.provider,
                "model": choice.model,
                "kind": failure.kind,
            },
        )
        if stopped:
            raise RouterError(failure.kind, str(failure), attempts=attempts)
    raise RouterError("exhausted", f"Every route for {resolved.value} failed", attempts=attempts)
