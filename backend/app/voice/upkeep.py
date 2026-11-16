from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Protocol

from app.core.errors import ExternalFailure
from app.providers.elevenlabs import ElevenLabs
from app.providers.quota import LedgerEntry

from .records import SessionRecord
from .seconds import ledger_entry, refund_key, settle_key

__all__ = [
    "FINISHED_STATUSES",
    "OWN_CALLS_LIMIT",
    "RECONCILE_LIMIT",
    "UpkeepReport",
    "UpkeepStore",
    "run_upkeep",
    "settle_own_calls",
]

logger = logging.getLogger(__name__)

FINISHED_STATUSES = frozenset({"done", "failed"})
RECONCILE_LIMIT = 200
OWN_CALLS_LIMIT = 5


class SettleStore(Protocol):
    async def unreconciled(self, limit: int, *, user_id: uuid.UUID | None = None) -> list[SessionRecord]: ...

    async def settle(self, record: SessionRecord, billed: int, entry: LedgerEntry | None) -> None: ...


class UpkeepStore(SettleStore, Protocol):
    async def close_lapsed(self, now: datetime) -> int: ...

    async def purge_transcripts(self, now: datetime) -> int: ...


@dataclass
class UpkeepReport:
    closed: int = 0
    purged: int = 0
    reconciled: int = 0
    refunded_seconds: int = 0
    charged_seconds: int = 0
    deleted: int = 0
    waiting: int = 0
    failures: list[str] = field(default_factory=list)


async def run_upkeep(store: UpkeepStore, elevenlabs: ElevenLabs | None, *, now: datetime) -> UpkeepReport:
    report = UpkeepReport(closed=await store.close_lapsed(now), purged=await store.purge_transcripts(now))
    if elevenlabs is None:
        return report
    for record in await store.unreconciled(RECONCILE_LIMIT):
        await _reconcile(record, store, elevenlabs, report)
    return report


async def settle_own_calls(user_id: uuid.UUID, store: SettleStore, elevenlabs: ElevenLabs) -> UpkeepReport:
    report = UpkeepReport()
    for record in await store.unreconciled(OWN_CALLS_LIMIT, user_id=user_id):
        await _reconcile(record, store, elevenlabs, report)
    for failure in report.failures:
        logger.warning("an ended voice call could not be settled yet: %s", failure)
    return report


async def _reconcile(
    record: SessionRecord, store: SettleStore, elevenlabs: ElevenLabs, report: UpkeepReport
) -> None:
    conversation_id = record.conversation_id or ""
    try:
        conversation = await elevenlabs.conversation(conversation_id)
    except ExternalFailure as error:
        if error.kind != "not_found":
            report.failures.append(f"{record.id}: {error}")
            return
        await store.settle(record, record.reserved_seconds, None)
        report.reconciled += 1
        return
    if conversation.status not in FINISHED_STATUSES:
        report.waiting += 1
        return
    billed = (
        record.reserved_seconds
        if conversation.call_duration_seconds is None
        else conversation.call_duration_seconds
    )
    await store.settle(record, billed, _settlement(record, billed))
    report.reconciled += 1
    report.refunded_seconds += max(0, record.reserved_seconds - billed)
    report.charged_seconds += max(0, billed - record.reserved_seconds)
    try:
        await elevenlabs.delete_conversation(conversation_id)
        report.deleted += 1
    except ExternalFailure as error:
        report.failures.append(f"{record.id}: delete failed: {error}")


def _settlement(record: SessionRecord, billed: int) -> LedgerEntry | None:
    difference = billed - record.reserved_seconds
    if difference < 0:
        return ledger_entry(record, units=difference, key=refund_key(record.id))
    if difference > 0:
        return ledger_entry(record, units=difference, key=settle_key(record.id))
    return None
