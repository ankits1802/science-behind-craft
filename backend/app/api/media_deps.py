from __future__ import annotations

from datetime import UTC, datetime
from functools import lru_cache

from app.core.config import get_settings
from app.core.db import sessionmaker
from app.core.security import secret_key_or_none
from app.media.bundle import BUNDLE_KEY_NAME
from app.media.jobs import MediaDeps
from app.media.store import SqlMediaStore
from app.providers.media_router import MediaRouter
from app.services.object_store import ObjectStore, object_store

__all__ = ["media_bucket", "media_deps"]


def media_deps() -> MediaDeps:
    settings = get_settings()
    return MediaDeps(
        store=SqlMediaStore(sessionmaker()),
        budget=MediaRouter(session_factory=sessionmaker()),
        links=media_bucket(),
        bundle_key=secret_key_or_none(BUNDLE_KEY_NAME, settings.media_bundle_hmac_key),
        now=datetime.now(UTC),
    )


def media_bucket() -> ObjectStore | None:
    settings = get_settings()
    return _links(settings.s3_bucket, settings.aws_region)


@lru_cache(maxsize=2)
def _links(bucket: str | None, region: str) -> ObjectStore | None:
    if not bucket:
        return None
    return object_store(get_settings())
