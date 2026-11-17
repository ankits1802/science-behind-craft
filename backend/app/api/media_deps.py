from __future__ import annotations

from datetime import UTC, datetime

from app.core.config import get_settings
from app.core.db import sessionmaker
from app.core.security import secret_key_or_none
from app.media.bundle import BUNDLE_KEY_NAME
from app.media.jobs import MediaDeps
from app.media.store import SqlMediaStore
from app.providers.media_router import MediaRouter
from app.services.object_store import media_bucket

__all__ = ["media_deps"]


def media_deps() -> MediaDeps:
    settings = get_settings()
    return MediaDeps(
        store=SqlMediaStore(sessionmaker()),
        budget=MediaRouter(session_factory=sessionmaker()),
        links=media_bucket(),
        bundle_key=secret_key_or_none(BUNDLE_KEY_NAME, settings.media_bundle_hmac_key),
        now=datetime.now(UTC),
    )
