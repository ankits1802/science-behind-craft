from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.services import managed_secrets
from app.sources.scholarly.registry import SCHOLARLY_KEY_NAMES, ScholarlyKeys

__all__ = ["scholarly_keys"]


async def scholarly_keys(session: AsyncSession) -> ScholarlyKeys:
    values = {name.lower(): await managed_secrets.get_secret(session, name) for name in SCHOLARLY_KEY_NAMES}
    return ScholarlyKeys(contact_email=str(get_settings().research_contact_email), **values)
