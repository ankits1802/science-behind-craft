from __future__ import annotations

from datetime import UTC, datetime
from functools import partial

from app.core.config import Settings
from app.core.db import sessionmaker
from app.providers.media_router import MediaRouter
from app.services.object_store import object_store

from .bundle import bundle_key
from .queue import MediaQueue
from .queue_store import SqlQueueStore
from .runner import RunnerDeps, abandon_job, run_job

__all__ = ["media_queue", "utc_now"]


def utc_now() -> datetime:
    return datetime.now(UTC)


def media_queue(settings: Settings, *, worker_id: str) -> MediaQueue:
    sessions = sessionmaker()
    store = SqlQueueStore(sessions)
    deps = RunnerDeps(
        store=store,
        generator=MediaRouter(session_factory=sessions),
        objects=object_store(settings),
        bundle_key=bundle_key(settings.media_bundle_hmac_key),
        clock=utc_now,
    )
    return MediaQueue(
        store=store,
        run=partial(run_job, deps),
        abandon=partial(abandon_job, deps),
        worker_id=worker_id,
        clock=utc_now,
    )
