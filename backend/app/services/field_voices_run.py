from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

import httpx

from app.core.config import Settings
from app.core.errors import NotConfigured
from app.research.embedding import TextEmbedder
from app.services.field_voices_images import ImageCopier
from app.services.field_voices_ledger import OpenSession, SqlFieldVoicesLedger
from app.services.field_voices_reader import field_voices_reader, image_hosts
from app.services.field_voices_store import ApplyContext
from app.services.field_voices_sync import PortalReport, SyncClock, sync_portal
from app.services.object_store import ObjectStore, object_store
from app.services.portal_craft_feed import PORTALS

__all__ = ["FieldVoicesRun", "run_field_voices"]


@dataclass
class FieldVoicesRun:
    enabled: bool
    error: str | None = None
    portals: list[PortalReport] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return self.error is None and all(portal.as_dict()["ok"] for portal in self.portals)

    def as_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "enabled": self.enabled,
            "error": self.error,
            "portals": [portal.as_dict() for portal in self.portals],
        }


async def run_field_voices(
    settings: Settings,
    *,
    open_session: OpenSession,
    embed: TextEmbedder,
    transports: Mapping[str, httpx.AsyncBaseTransport] | None = None,
    clock: SyncClock | None = None,
) -> FieldVoicesRun:
    if not settings.field_voices_enabled:
        return FieldVoicesRun(enabled=False)
    try:
        hosts = image_hosts(settings.field_voices_image_hosts)
    except NotConfigured as error:
        return FieldVoicesRun(enabled=True, error=error.message)
    store = object_store(settings) if settings.s3_bucket else None
    ledger = SqlFieldVoicesLedger(
        open_session,
        embed=embed,
        store=store,
        context=ApplyContext(
            now=datetime.now(UTC), web_base=settings.public_web_url, api_base=settings.public_api_url
        ),
    )
    copier = _copier(settings, store, hosts, (transports or {}).get("images"))
    run = FieldVoicesRun(enabled=True)
    for portal in PORTALS:
        run.portals.append(
            await _portal(
                settings,
                portal,
                ledger=ledger,
                copier=copier,
                transports=transports,
                clock=clock or SyncClock(),
            )
        )
    return run


async def _portal(
    settings: Settings,
    portal: str,
    *,
    ledger: SqlFieldVoicesLedger,
    copier: ImageCopier | None,
    transports: Mapping[str, httpx.AsyncBaseTransport] | None,
    clock: SyncClock,
) -> PortalReport:
    try:
        reader = field_voices_reader(settings, portal, transport=(transports or {}).get(portal))
    except NotConfigured as error:
        return PortalReport(portal=portal, ok=False, error=error.message)
    return await sync_portal(reader, ledger, copier, clock=clock)


def _copier(
    settings: Settings,
    store: ObjectStore | None,
    hosts: frozenset[str],
    transport: httpx.AsyncBaseTransport | None,
) -> ImageCopier | None:
    if store is None or not (settings.public_api_url or "").startswith("https://"):
        return None
    return ImageCopier(store, image_hosts=hosts, transport=transport)
