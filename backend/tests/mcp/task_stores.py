from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime

from app.services.mcp_task_store import WORKING, HeldTasks, TaskEnding, TaskRecord


@dataclass
class HeldTaskStore:
    records: dict[str, TaskRecord] = field(default_factory=dict)
    beats: list[str] = field(default_factory=list)

    async def add(self, record: TaskRecord) -> None:
        self.records[record.task_id] = record

    async def read(self, task_id: str) -> TaskRecord | None:
        return self.records.get(task_id)

    async def end(self, task_id: str, ending: TaskEnding, *, now: datetime) -> bool:
        record = self.records.get(task_id)
        if record is None or record.status != WORKING:
            return False
        self.records[task_id] = replace(
            record,
            status=ending.status,
            status_message=ending.said,
            result=ending.result,
            error=ending.error,
            updated_at=now,
        )
        return True

    async def beat(self, task_id: str, *, now: datetime) -> bool:
        record = self.records.get(task_id)
        if record is None or record.status != WORKING:
            return False
        self.beats.append(task_id)
        self.records[task_id] = replace(record, heartbeat_at=now)
        return True

    async def held(self, principal: str, *, now: datetime) -> HeldTasks:
        live = [record for record in self.records.values() if not record.expired(now)]
        return HeldTasks(mine=sum(record.principal == principal for record in live), everyone=len(live))
